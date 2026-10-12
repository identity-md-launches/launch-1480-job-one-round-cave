"""Offline checks using retained real mainnet ZTO evidence, then mutations."""
import copy
import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest import mock
import crosscheck as c


class CrosscheckTests(unittest.TestCase):
    def setUp(self):
        self.left, self.right = [json.loads((Path(__file__).parent / name).read_text())
                                 for name in ("publicnode.json", "drpc.json")]

    def refresh(self, capture):
        events, duplicates = c.window.validate_logs(capture["raw_logs"], capture["decimals"],
            capture["token_address"], capture["from_block"], capture["to_block"])
        capture.update(transfers=events, duplicate_count=duplicates, transfer_count=len(events))

    def test_real_agreement(self):
        r = c.compare(self.left, self.right)
        self.assertEqual(r["status"], "agreement")
        self.assertEqual(r["transfer_counts"], [3, 3])

    def test_missing_event_is_disagreement(self):
        removed = self.right["raw_logs"].pop(0)
        self.refresh(self.right)
        r = c.compare(self.left, self.right)
        self.assertEqual(r["status"], "disagreement")
        self.assertEqual(len(r["only_left"]), 1)
        self.assertEqual(r["only_left"][0]["transaction_hash"], removed["transactionHash"])

    def test_conflicting_event(self):
        self.right["raw_logs"][0]["data"] = "0x" + format(123, "064x")
        self.refresh(self.right)
        self.assertEqual(len(c.compare(self.left, self.right)["conflicts"]), 1)

    def test_boundary_disagreement(self):
        # First boundary in the real fixture has no event, so this is valid but different evidence.
        self.right["from_block_anchor"]["hash"] = "0x" + "ab" * 32
        r = c.compare(self.left, self.right)
        self.assertIn("from_block_anchor", r["metadata_differences"])
        self.assertEqual(r["status"], "disagreement")

    def test_duplicates_do_not_create_disagreement(self):
        self.right["raw_logs"].append(copy.deepcopy(self.right["raw_logs"][0]))
        self.refresh(self.right)
        self.assertEqual(c.compare(self.left, self.right)["status"], "agreement")

    def test_order_does_not_create_disagreement(self):
        self.right["raw_logs"].reverse()
        self.refresh(self.right)
        self.assertEqual(c.compare(self.left, self.right)["status"], "agreement")

    def test_malformed_captures_fail(self):
        mutations = [("chain_id", True), ("schema_version", True), ("rpc", False),
                     ("decimals", 256), ("transfer_count", 0), ("decimals_block", 1),
                     ("from_block", -1), ("raw_logs", None), ("transfers", []),
                     ("read_only", 1), ("provider_result", "unvalidated")]
        for key, value in mutations:
            with self.subTest(key=key):
                bad = copy.deepcopy(self.right)
                bad[key] = value
                with self.assertRaises(c.window.RpcError):
                    c.compare(self.left, bad)

    def test_raw_evidence_is_revalidated(self):
        self.right["raw_logs"][0]["removed"] = True
        with self.assertRaises(c.window.RpcError):
            c.compare(self.left, self.right)

    def test_same_url_rejected(self):
        self.right["rpc"] = self.left["rpc"] + "/"
        with self.assertRaises(c.window.RpcError):
            c.compare(self.left, self.right)

    def test_distinct_ranges_disagree(self):
        self.right["from_block"] -= 1
        self.right["from_block_anchor"]["number"] -= 1
        self.assertIn("from_block", c.compare(self.left, self.right)["metadata_differences"])

    def produced(self, summary=True):
        """Run the real producer against retained real replies, not schema relabeling."""
        evidence = self.left
        anchors = {evidence[key]["number"]: evidence[key]["hash"]
                   for key in ("from_block_anchor", "to_block_anchor")}

        def replies(endpoint, method, params):
            if method == "eth_chainId": return "0x1"
            if method == "eth_blockNumber": return hex(evidence["head_at_capture"])
            if method == "eth_call": return "0x" + format(evidence["decimals"], "064x")
            if method == "eth_getLogs": return copy.deepcopy(evidence["raw_logs"])
            if method == "eth_getBlockByNumber":
                number = int(params[0], 16)
                return {"number": hex(number), "hash": anchors[number]}
            raise AssertionError(method)

        args = ["--from-block", str(evidence["from_block"]),
                "--to-block", str(evidence["to_block"])]
        if summary:
            args += ["--address", evidence["transfers"][0]["to"]]
        output = io.StringIO()
        with mock.patch.object(c.window, "rpc", side_effect=replies), \
                contextlib.redirect_stdout(output):
            c.window.main(args)
        return json.loads(output.getvalue())

    def test_current_producer_to_crosscheck_and_receipt(self):
        receipt_spec = c.importlib.util.spec_from_file_location(
            "receipt", Path(__file__).parent.parent / "transfer-window-receipt" / "receipt.py")
        receipt = c.importlib.util.module_from_spec(receipt_spec)
        receipt_spec.loader.exec_module(receipt)
        for summary in (False, True):
            with self.subTest(summary=summary):
                produced = self.produced(summary)
                self.assertEqual(produced["schema_version"], 3)
                self.assertEqual(c.compare(produced, self.right)["status"], "agreement")
                self.assertEqual(receipt.receipt(produced)["window_sha256"],
                                 receipt.receipt(self.left)["window_sha256"])

    def test_schema3_summary_tampering_rejected_by_both_companions(self):
        receipt_spec = c.importlib.util.spec_from_file_location(
            "receipt", Path(__file__).parent.parent / "transfer-window-receipt" / "receipt.py")
        receipt = c.importlib.util.module_from_spec(receipt_spec)
        receipt_spec.loader.exec_module(receipt)
        produced = self.produced()
        mutations = [("received_raw", "0"), ("net", "0"), ("scope", "balance"),
                     ("matching_transfer_count", True), ("incoming_transfer_count", 1.0),
                     ("address", "invalid"), ("address", produced["address_window_summary"]["address"].upper()),
                     ("extra", "unchecked")]
        for key, value in mutations:
            bad = copy.deepcopy(produced)
            bad["address_window_summary"][key] = value
            with self.subTest(key=key):
                with self.assertRaises(c.window.RpcError): c.checked(bad)
                with self.assertRaises(receipt.crosscheck.window.RpcError): receipt.receipt(bad)
        for summary in (None, [], False):
            bad = copy.deepcopy(produced)
            bad["address_window_summary"] = summary
            with self.assertRaises(c.window.RpcError): c.checked(bad)

    def test_legacy_summary_and_unknown_schema_rejected(self):
        bad = self.produced()
        bad["schema_version"] = 2
        with self.assertRaises(c.window.RpcError): c.checked(bad)
        for schema in (1, 4, True, "3", 3.0):
            bad = self.produced(False)
            bad["schema_version"] = schema
            with self.assertRaises(c.window.RpcError): c.checked(bad)

    def test_live_mode_pins_same_range(self):
        with mock.patch.object(c.window, "rpc", side_effect=["0x1", hex(26177321)]), \
                mock.patch.object(c, "capture", side_effect=[self.left, self.right]) as acquire, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(c.main([]), 0)
        self.assertEqual([call.args[1:] for call in acquire.call_args_list],
                         [("zto", 26177298, 26177309)] * 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "agreement")

    def test_second_provider_failure_has_no_agreement_output(self):
        with mock.patch.object(c, "capture", side_effect=[self.left, c.window.RpcError("offline")]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(c.window.RpcError):
                c.main(["--from-block", "26177298", "--to-block", "26177309"])
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
