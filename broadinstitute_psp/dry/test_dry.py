"""
This code should be run from broadinstitute_psp.

The dry directory contains a directory called functional_tests
that has the assets required for the 3 functional tests below. For
functional tests, I just check that they run to completion.

"""

import unittest
import logging
import os
import numpy as np
import pandas as pd

import cmap.io.GCToo as GCToo
import broadinstitute_psp.utils.setup_logger as setup_logger
import dry

# Setup logger
logger = logging.getLogger(setup_logger.LOGGER_NAME)

# Functional tests dir lives within the dry directory
FUNCTIONAL_TESTS_DIR = "dry/functional_tests"

# Set to false if you want to see what output is created
CLEANUP = True

# N.B. e_out is expected_output.
class TestDry(unittest.TestCase):

    def test_read_dry_gct_and_config_file(self):
        PSP_CONFIG_PATH = "psp_production.cfg"
        INPUT_GCT_PATH = os.path.join(FUNCTIONAL_TESTS_DIR, "p100_prm_plate29_3H.gct")
        e_data_df_shape = (96, 96)
        e_assay_type = "p100"
        e_prov_code = ["PRM", "L2X"]
        e_gcp_norm_peptide = "BI10052"

        # Happy path
        (out_gct, out_assay_type, out_prov_code, config_io, config_metadata,
         config_parameters) = dry.read_dry_gct_and_config_file(
            INPUT_GCT_PATH, PSP_CONFIG_PATH, None)

        self.assertEqual(out_gct.data_df.shape, e_data_df_shape,
                         ("The expected shape of the data matrix is {}, " +
                          "not {}").format(e_data_df_shape, out_gct.data_df.shape))
        self.assertEqual(out_assay_type, e_assay_type,
                         ("The expected assay type is {}, " +
                          "not {}").format(e_assay_type, out_assay_type))
        self.assertEqual(out_prov_code, e_prov_code,
                         ("The expected provenance code is {}, " +
                          "not {}").format(e_prov_code, out_prov_code))
        self.assertEqual(config_metadata["gcp_normalization_peptide_id"],
                         e_gcp_norm_peptide,
                         ("The expected gcp_normalization_peptide_id is {}" +
                          "").format(e_gcp_norm_peptide, config_metadata["gcp_normalization_peptide_id"]))

        # Check that force-assay works
        e_forced_assay_type = "gcp"
        (_, out_forced_assay_type, _, _, _, _) = dry.read_dry_gct_and_config_file(
            INPUT_GCT_PATH, PSP_CONFIG_PATH, "GR1")
        self.assertEqual(out_forced_assay_type, e_forced_assay_type,
                         ("The expected assay type is {}, " +
                          "not {}").format(e_forced_assay_type, out_forced_assay_type))

    def test_extract_prov_code(self):
        col_meta_df = pd.DataFrame.from_dict({"foo": ["a", "b", "c"],
                                              "prov_field": ["PRM+L2X",
                                                             "PRM+L2X",
                                                             "PRM+L2X"]})
        e_prov_code = ["PRM", "L2X"]
        prov_code = dry.extract_prov_code(col_meta_df, "prov_field", "+")
        self.assertEqual(e_prov_code, prov_code,
                        ("The expected provenance code is {}, " +
                         "not {}").format(e_prov_code, prov_code))

    def test_check_assay_type(self):
        assay_type = "aBc"
        p100 = ["ABC", "aBc", "d"]
        gcp = ["bd", "ef"]
        assay_out = dry.check_assay_type(assay_type, p100, gcp)
        self.assertEqual(assay_out, "p100")


    def test_log_transform_if_needed(self):
        prov_code = ["GR1", "L2X"]
        in_df = pd.DataFrame([[10, -3, 1.2],
                              [0.45, 0.2, 0],
                              [4.5, np.nan, 0.3]], dtype=float)

        in_gct = GCToo.GCToo.GCToo(data_df=in_df, row_metadata_df=None, col_metadata_df=None)

        # Nothing should happen
        (out_gct, out_prov_code) = dry.log_transform_if_needed(in_gct, prov_code, "L2X")
        self.assertTrue(np.allclose(out_gct.data_df, in_df, atol=1e-3, equal_nan=True))
        self.assertEqual(out_prov_code, prov_code)

        # L2X should occur
        prov_code2 = ["GR1"]
        (_, out_prov_code2) = dry.log_transform_if_needed(in_gct, prov_code2, "L2X")
        self.assertEqual(out_prov_code2, prov_code)


    def test_log_transform(self):
        in_df = pd.DataFrame([[10, -3, 1.2],
                              [0.45, 0.2, 0],
                              [4.5, np.nan, 0.3]], dtype=float)
        e_df = pd.DataFrame([[3.322, np.nan, 0.263],
                             [-1.152, -2.322, np.nan],
                             [2.170, np.nan, -1.737]], dtype=float)
        out_df = dry.log_transform(in_df, log_base=2)
        self.assertTrue(np.allclose(out_df, e_df, atol=1e-3, equal_nan=True),
                        ("\nExpected output:\n{} " +
                         "\nActual output:\n{}").format(e_df, out_df))

    def test_gcp_histone_normalize_if_needed(self):
        data = pd.DataFrame([[1, 2], [3, 4], [5, 6]],
                            index=["a", "b", "c"],
                            columns=["d", "e"])
        e_data = pd.DataFrame([[-2, -2], [2, 2]],
                            index=["a", "c"],
                            columns=["d", "e"])
        row_meta = pd.DataFrame([["rm1", "rm2"],["rm3", "rm4"],["rm5", "rm6"]],
                                index=["a", "b", "c"],
                                columns=["row_field1", "row_field2"])
        e_row_meta = pd.DataFrame([["rm1", "rm2"],["rm5", "rm6"]],
                                index=["a", "c"],
                                columns=["row_field1", "row_field2"])
        col_meta = pd.DataFrame([["cm1", "cm2"],["cm3", "cm4"]],
                                index=["d", "e"],
                                columns=["col_field1", "col_field2"])
        in_gct = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta, col_metadata_df=col_meta)
        assay_type = "gcp"
        norm_peptide = "b"
        prov_code = ["GR1", "L2X"]
        e_prov_code = ["GR1", "L2X", "H3N"]

        # Happy path
        (out_gct, out_prov_code) = dry.gcp_histone_normalize_if_needed(
            in_gct, assay_type, norm_peptide, prov_code, "H3N")

        self.assertTrue(np.allclose(out_gct.data_df, e_data, atol=1e-3))
        self.assertTrue(np.array_equal(out_gct.row_metadata_df, e_row_meta))
        self.assertTrue(np.array_equal(out_gct.col_metadata_df, in_gct.col_metadata_df))
        self.assertEqual(out_prov_code, e_prov_code)

        # GCP but no peptide ID
        (out_gct2, out_prov_code2) = dry.gcp_histone_normalize_if_needed(
            in_gct, assay_type, None, prov_code, "H3N")

        self.assertTrue(np.allclose(out_gct2.data_df, data, atol=1e-3))
        self.assertTrue(np.array_equal(out_gct2.row_metadata_df, row_meta))
        self.assertTrue(np.array_equal(out_gct2.col_metadata_df, col_meta))
        self.assertEqual(out_prov_code2, prov_code)

    def test_gcp_histone_normalize(self):
        df = pd.DataFrame([[1.1, 2.0, 3.3], [4.1, 5.8, 6.0]],
                          index=["a", "b"],
                          columns=["c1", "c2", "c3"])
        e_df = pd.DataFrame([[3.0, 3.8, 2.7]],
                          index=["b"],
                          columns=["c1", "c2", "c3"])

        out_df = dry.gcp_histone_normalize(df, "a")
        self.assertTrue(out_df.shape == e_df.shape,
                        ("expected_out.shape: {} not the same " +
                         "as actual_out.shape: {}").format(e_df.shape, out_df.shape))
        self.assertTrue(np.allclose(out_df, e_df, atol=1e-3, equal_nan=True),
                        ("\nExpected output:\n{} " +
                         "\nActual output:\n{}").format(e_df, out_df))

    def test_initial_filtering(self):
        sample_frac_cutoff = 0.3
        probe_frac_cutoff = 0.5
        probe_sd_cutoff = 3
        assay_type = "p100"
        manual_rejection_field = "rej"
        prov_code = ["A", "B"]
        e_prov_code = ["A", "B", "SF3", "MPR", "PF5"]
        e_remaining_samples = ["e", "f", "g"]

        data = pd.DataFrame([[1, 2, 3], [np.nan, 5, np.nan], [7, 8, 9], [10, 11, 12]],
                            index=["a", "b", "c", "d"],
                            columns=["e", "f", "g"])
        e_data = pd.DataFrame([[1, 2, 3], [7, 8, 9]],
                              index=["a", "c",],
                              columns=["e", "f", "g"])
        row_meta = pd.DataFrame([["rm1", "TRUE"],["rm3", "TRUE"],["rm5", "TRUE"],["rm7", "FALSE"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_field1", "rej"])
        e_row_meta = pd.DataFrame([["rm1", "TRUE"],["rm5", "TRUE"]],
                                index=["a", "c"],
                                columns=["row_field1", "rej"])
        col_meta = pd.DataFrame([["cm1", "cm2"],["cm3", "cm4"],["cm5", "cm6"]],
                                index=["e", "f", "g"],
                                columns=["col_field1", "col_field2"])
        in_gct = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta, col_metadata_df=col_meta)
        original_gct = in_gct

        (out_gct, out_prov_code, out_remaining) = dry.initial_filtering(
            in_gct, assay_type, sample_frac_cutoff, probe_frac_cutoff,
            probe_sd_cutoff, {}, manual_rejection_field, prov_code,
            "SF", "MPR", "PF")

        self.assertTrue(np.allclose(out_gct.data_df, e_data, atol=1e-3))
        self.assertTrue(np.array_equal(out_gct.row_metadata_df, e_row_meta))
        self.assertTrue(np.array_equal(out_gct.col_metadata_df, col_meta))
        self.assertEqual(out_remaining, e_remaining_samples)
        self.assertEqual(out_prov_code, e_prov_code)

        # Make sure that input gct was not modified
        self.assertTrue(np.allclose(in_gct.data_df, original_gct.data_df,
                                    atol=1e-3, equal_nan=True))

        # Check that manual rejection doesn't happen if no probes marked for rejection
        row_meta2 = pd.DataFrame([["rm1", "TRUE"],["rm3", "TRUE"],["rm5", "TRUE"],["rm7", "TRUE"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_field1", "rej"])
        e_data2 = pd.DataFrame([[1, 2, 3], [7, 8, 9], [10, 11, 12]],
                              index=["a", "c", "d"],
                              columns=["e", "f", "g"])
        e_prov_code2 = ["A", "B", "SF3", "PF5"]

        in_gct2 = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta2, col_metadata_df=col_meta)
        (out_gct2, out_prov_code2, out_remaining2) = dry.initial_filtering(
            in_gct2, assay_type, sample_frac_cutoff, probe_frac_cutoff,
            probe_sd_cutoff, {},
            manual_rejection_field, prov_code,
            "SF", "MPR", "PF")

        self.assertTrue(np.allclose(out_gct2.data_df, e_data2, atol=1e-3))
        self.assertEqual(out_remaining2, e_remaining_samples)
        self.assertEqual(out_prov_code2, e_prov_code2)

    def test_check_assay_specific_thresh(self):
        assay_type = "p100"
        sample_frac_cutoff = None
        probe_frac_cutoff = 0.5
        probe_sd_cutoff = None
        config_parameters = {"gcp_sample_frac_cutoff": "0.1",
                             "gcp_probe_frac_cutoff": "0.2",
                             "p100_sample_frac_cutoff": "0.3",
                             "p100_probe_frac_cutoff": "0.4",
                             "gcp_probe_sd_cutoff": "0.5",
                             "p100_probe_sd_cutoff": "0.6"}
        e_sample_frac_cutoff = 0.3
        e_probe_frac_cutoff = 0.5
        e_probe_sd_cutoff = 0.6
        [out_sample_thresh, out_probe_thresh, out_probe_sd_cutoff] = (
            dry.check_assay_specific_thresh(
                assay_type, sample_frac_cutoff, probe_frac_cutoff,
                probe_sd_cutoff, config_parameters))

        self.assertEqual(e_sample_frac_cutoff, out_sample_thresh)
        self.assertEqual(e_probe_frac_cutoff, out_probe_thresh)
        self.assertEqual(e_probe_sd_cutoff, out_probe_sd_cutoff)

    def test_filter_samples_by_nan(self):
        df = pd.DataFrame(np.array([[0.5, 0.2, 0.1, 0.25],
                                    [np.nan, 0.45, 0.2, -0.1],
                                    [np.nan, 0.02, np.nan, 0.3]], dtype=float))
        e_out = pd.DataFrame(np.array([[0.2, 0.1, 0.25],
                                       [0.45, 0.2, -0.1],
                                       [0.02, np.nan, 0.3]], dtype=float))
        out = dry.filter_samples_by_nan(df, sample_frac_cutoff=0.6)
        self.assertTrue(out.shape == e_out.shape,
                        ("expected_out.shape: {} not the same " +
                         "as actual_out.shape: {}").format(e_out.shape, out.shape))

        self.assertTrue(np.allclose(out, e_out, equal_nan=True),
                        ("\nExpected output:\n{} " +
                         "\nActual output:\n{}").format(e_out, out))

    def test_manual_probe_rejection(self):
        manual_rejection_field = "pr_probe_suitability_manual"
        row_meta_df = pd.DataFrame({"foo": ["a", "b", "c"],
                                    "pr_probe_suitability_manual": ["TRUE", "TRUE", "FALSE"],
                                    "bar": ["d", "e", "f"]})
        data_df = pd.DataFrame(np.array([[10, -3, 1.2],
                                         [0.45, 0.2, 0],
                                         [4.5, np.nan, 0.3]], dtype=float))
        e_df = pd.DataFrame(np.array([[10, -3, 1.2], [0.45, 0.2, 0]], dtype=float))
        out_df = dry.manual_probe_rejection(data_df, row_meta_df, manual_rejection_field)

        self.assertTrue(np.allclose(out_df, e_df, atol=1e-3, equal_nan=True),
                        ("\nExpected df:\n{} " +
                         "\nActual df:\n{}").format(e_df, out_df))

    def test_filter_probes_by_nan_and_sd(self):
        df = pd.DataFrame(np.array([[10, 0.2, 0.1, 0.25],
                                    [np.nan, 0.45, 0.2, -0.1],
                                    [np.nan, 0.02, np.nan, 0.3]], dtype=float))
        e_out = df.iloc[[1], :]
        out = dry.filter_probes_by_nan_and_sd(df, probe_frac_cutoff=0.6, probe_sd_cutoff=3)
        self.assertTrue(out.shape == e_out.shape,
                        ("expected_out.shape: {} not the same " +
                         "as actual_out.shape: {}").format(e_out.shape, out.shape))
        self.assertTrue(np.allclose(out, e_out, equal_nan=True),
                        ("\nExpected output:\n{} " +
                         "\nActual output:\n{}").format(e_out, out))

    def test_p100_calculate_dists_and_apply_offsets_if_needed(self):
        no_optim = True
        offset_bounds = (-2, 2)
        prov_code = ["PR1", "L2X", "filtering"]
        e_dists = [14.75, 0.0, 4.75]
        e_offsets = [3.25, 0.0, -2.25]
        e_prov_code = ["PR1", "L2X", "filtering", "LLB"]

        data = pd.DataFrame([[1, 2, 3],[5, 7, 11], [13, 17, 19], [23, 29, 31]],
                            index=["a", "b", "c", "d"],
                            columns=["e", "f", "g"], dtype=float)
        row_meta = pd.DataFrame([["rm1", "rm2"],["rm3", "rm4"],["rm5", "rm6"],["rm7", "rm8"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_field1", "row_field2"])
        col_meta = pd.DataFrame([["cm1", "cm2"],["cm3", "cm4"],["cm5", "cm6"]],
                                index=["e", "f", "g"],
                                columns=["col_field1", "col_field2"])
        in_gct = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta, col_metadata_df=col_meta)

        # P100 & optim
        (out_gct, out_dists, out_offsets, out_prov_code) = (
            dry.p100_calculate_dists_and_apply_offsets_if_needed(
                in_gct, "p100", no_optim_bool=False,
                offset_bounds=offset_bounds, prov_code=prov_code,
                prov_code_entry="LLB"))

        self.assertTrue(np.allclose(out_offsets, e_offsets, atol=1e-2), (
            "out_offsets:\n{}\ne_offsets:\n{}".format(out_offsets, e_offsets)))
        self.assertTrue(np.allclose(out_dists, e_dists, atol=1e-2), (
            "out_dists:\n{}\ne_dists:\n{}".format(out_dists, e_dists)))
        self.assertTrue(np.allclose(out_offsets, e_offsets, atol=1e-2))
        self.assertEqual(out_prov_code, e_prov_code)

        # P100 but no optim
        e_dists2 = [57, 0, 25]
        (out_gct, out_dists, out_offsets, out_prov_code) = (
            dry.p100_calculate_dists_and_apply_offsets_if_needed(
                in_gct, "p100", no_optim_bool=True,
                offset_bounds=offset_bounds, prov_code=prov_code,
                prov_code_entry="LLB"))

        self.assertTrue(np.allclose(out_dists, e_dists2, atol=1e-2), (
            "out_dists:\n{}\ne_dists2:\n{}".format(out_dists, e_dists2)))
        self.assertEqual(out_offsets, None)
        self.assertEqual(out_prov_code, prov_code)

        # GCP
        (out_gct, out_dists, out_offsets, out_prov_code) = (
            dry.p100_calculate_dists_and_apply_offsets_if_needed(
                in_gct, "gcp", no_optim_bool=True,
                offset_bounds=offset_bounds, prov_code=prov_code,
                prov_code_entry="LLB"))

        self.assertEqual(out_dists, None)
        self.assertEqual(out_offsets, None)
        self.assertEqual(out_prov_code, prov_code)

    def test_calculate_distances_and_optimize(self):
        df = pd.DataFrame([[10, -3, 1.2],
                           [0.45, 0.2, -0.1],
                           [4.5, -4, 0.3]], dtype=float)
        e_df = pd.DataFrame([[5.58, -0.16, 1.30],
                             [-3.96, 3.03, 0],
                             [0.08, -1.16, 0.40]], dtype=float)
        e_offsets = np.array([-4.42, 2.83, 0.10], dtype=float)
        e_dists = np.array([36.62, 12.04, 0.06], dtype=float)
        (out_df, offsets, dists) = dry.calculate_distances_and_optimize(df, (-7, 7))
        self.assertTrue(np.allclose(offsets, e_offsets, atol=1e-2),
                        ("\nExpected offsets:\n{} " +
                         "\nActual offsets:\n{}").format(e_offsets, offsets))
        self.assertTrue(np.allclose(dists, e_dists, atol=1e-2),
                        ("\nExpected distances:\n{} " +
                         "\nActual distances:\n{}").format(e_dists, dists))
        self.assertTrue(np.allclose(out_df, e_df, atol=1e-2),
                        ("\nExpected out_df:\n{} " +
                         "\nActual out_df:\n{}").format(e_df, out_df))

    def test_calculate_distances(self):
        df = pd.DataFrame([[10, 3, 1.2],
                           [0.45, 0.2, np.nan],
                           [4.5, 4, 0.3]], dtype=float)
        e_dists = np.array([49.27, 0.02, 16.93])
        out_dists = dry.calculate_distances(df)

        self.assertTrue(np.allclose(e_dists, out_dists, atol=1e-2),
                        ("The expected distances are {}, " +
                         "not {}.").format(e_dists, out_dists))

    def test_distance_function(self):
        values = np.array([1, 2.5, np.nan, 4, 5])
        medians = np.array([2, 0.5, 0.1, 1.1, 1.5])
        e_out = 25.66
        out = dry.distance_function(values, medians)
        self.assertTrue(np.isclose(out, e_out),
                        ("\nExpected output: {} " +
                         "\nActual output: {}").format(e_out, out))


    def test_p100_filter_samples_by_dist(self):
        offsets = np.array([4, 3, 7], dtype=float)
        dists = np.array([1, 6, 2], dtype=float)
        dist_sd_cutoff = 1
        prov_code = ["A", "B"]
        data = pd.DataFrame([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]],
                            index=["a", "b", "c", "d"],
                            columns=["e", "f", "g"])
        row_meta = pd.DataFrame([["rm1", "rm2"],["rm3", "rm4"],["rm5", "rm6"],["rm7", "rm8"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_field1", "row_field2"])
        col_meta = pd.DataFrame([["cm1", "cm2"],["cm3", "cm4"],["cm5", "cm6"]],
                                index=["e", "f", "g"],
                                columns=["col_field1", "col_field2"])
        in_gct = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta, col_metadata_df=col_meta)

        # P100
        e_data = pd.DataFrame([[1, 3], [4, 6], [7, 9], [10, 12]],
                            index=["a", "b", "c", "d"],
                            columns=["e", "g"])
        e_col_meta = pd.DataFrame([["cm1", "cm2"],["cm5", "cm6"]],
                                index=["e", "g"],
                                columns=["col_field1", "col_field2"])
        e_offsets = np.array([4, 7], dtype=float)
        e_remaining = ["e", "g"]
        e_prov_code = ["A", "B", "OSF1"]

        (out_gct, out_offsets, out_remaining, out_prov_code) = (
            dry.p100_filter_samples_by_dist(
                in_gct, "p100", offsets, dists, dist_sd_cutoff, prov_code, "OSF"))

        self.assertTrue(np.allclose(out_gct.data_df, e_data, atol=1e-2))
        self.assertTrue(np.array_equal(out_gct.col_metadata_df, e_col_meta))
        self.assertTrue(np.array_equal(out_gct.row_metadata_df, row_meta))
        self.assertTrue(np.allclose(out_offsets, e_offsets, atol=1e-2))
        self.assertEqual(out_remaining, e_remaining)
        self.assertEqual(out_prov_code, e_prov_code)

        # GCP
        (out_gct2, out_offsets2, out_remaining2, out_prov_code2) = (
            dry.p100_filter_samples_by_dist(
                in_gct, "gcp", None, dists, dist_sd_cutoff, prov_code, "OSF"))

        self.assertTrue(np.allclose(out_gct2.data_df, data, atol=1e-2))
        self.assertTrue(np.array_equal(out_gct2.col_metadata_df, col_meta))
        self.assertTrue(np.array_equal(out_gct2.row_metadata_df, row_meta))
        self.assertEqual(out_offsets2, None)
        self.assertEqual(out_remaining2, None)
        self.assertEqual(out_prov_code2, prov_code)


    def test_remove_sample_outliers(self):
        df = pd.DataFrame([[10, -3, 1.2, 0.6],
                           [0.45, 0.2, 0, 0.2],
                           [4.5, np.nan, 0.3, 0.4]], dtype=float)
        offsets = np.array([1, 2, 3, 4], dtype=float)
        dists = np.array([0.2, 5, 0.5, 0.4], dtype=float)
        (out, out_offsets) = dry.remove_sample_outliers(df, offsets, dists, dist_sd_cutoff=1)
        e_out = df.iloc[:, [0, 2, 3]]
        e_out_offsets = np.array([1, 3, 4])
        self.assertTrue(out.shape == e_out.shape, (
            "expected_out.shape: {} not the same " +
            "as actual_out.shape: {}").format(e_out.shape, out.shape))
        self.assertTrue(np.array_equal(out_offsets, e_out_offsets),
                        ("\nExpected out:\n{} " +
                         "\nActual out:\n{}").format(e_out_offsets, out_offsets))

    def test_median_normalize(self):
        data = pd.DataFrame([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]],
                            index=["a", "b", "c", "d"],
                            columns=["e", "f", "g"],
                            dtype=float)
        row_meta = pd.DataFrame([["1", "rm2"],["1", "rm4"],["1", "rm6"],["1", "rm8"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_subset", "row_field2"])
        col_meta = pd.DataFrame([["cm1", "1"],["cm3", "2"],["cm5", "2"]],
                                index=["e", "f", "g"],
                                columns=["col_field1", "col_subset"])
        in_gct = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta, col_metadata_df=col_meta)
        row_subset_field = "row_subset"
        col_subset_field = "col_subset"
        prov_code = ["A", "B"]

        # Subset normalize
        ignore_subset_norm = False
        e_data = pd.DataFrame([[0, -0.5, 0.5], [0, -0.5, 0.5], [0, -0.5, 0.5],[0, -0.5, 0.5]],
                            index=["a", "b", "c", "d"],
                            columns=["e", "f", "g"])
        e_prov_code = ["A", "B", "GMN"]

        (out_gct, out_prov_code) = dry.median_normalize(
            in_gct, ignore_subset_norm, row_subset_field, col_subset_field, prov_code,
            "GMN", "RMN")

        self.assertTrue(np.allclose(out_gct.data_df, e_data, atol=1e-2))
        self.assertTrue(np.array_equal(out_gct.row_metadata_df, row_meta))
        self.assertTrue(np.array_equal(out_gct.col_metadata_df, col_meta))
        self.assertEqual(out_prov_code, e_prov_code)

        # Ordinary normalization
        ignore_subset_norm2 = True
        e_data2 = pd.DataFrame([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1], [-1, 0, 1]],
                               index=["a", "b", "c", "d"],
                               columns=["e", "f", "g"],
                               dtype=float)
        row_meta2 = pd.DataFrame([["1", "rm2"],["1", "rm4"],["1", "rm6"],["1", "rm8"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_subset", "row_field2"])
        col_meta2 = pd.DataFrame([["cm1", "1"],["cm3", "1"],["cm5", "1"]],
                                index=["e", "f", "g"],
                                columns=["col_field1", "col_subset"])
        in_gct2 = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta2, col_metadata_df=col_meta2)
        e_prov_code2 = ["A", "B", "RMN"]

        (out_gct2, out_prov_code2) = dry.median_normalize(
            in_gct2, ignore_subset_norm2, row_subset_field, col_subset_field, prov_code,
            "GMN", "RMN")

        self.assertTrue(np.allclose(out_gct2.data_df, e_data2, atol=1e-2))
        self.assertTrue(np.array_equal(out_gct2.row_metadata_df, row_meta2))
        self.assertTrue(np.array_equal(out_gct2.col_metadata_df, col_meta2))
        self.assertEqual(out_prov_code2, e_prov_code2)


    def test_check_for_subsets(self):
        row_meta = pd.DataFrame([["rm1", "rm2"],["rm3", "rm4"],
                                 ["rm5", "rm6"],["rm7", "rm8"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_field1", "row_field2"])
        col_meta = pd.DataFrame([["cm1", "cm2"],["cm3", "cm4"],["cm5", "cm6"]],
                                index=["e", "f", "g"],
                                columns=["col_field1", "col_field2"])
        row_field = "row_field1"
        col_field = "col_field2"
        subsets_exist = dry.check_for_subsets(row_meta, col_meta, row_field, col_field)

        self.assertTrue(subsets_exist)


    def test_row_median_normalize(self):
        df = pd.DataFrame(np.array([[10, -3, 1.2, 0.6],
                                    [0.45, 0.2, 0, 0.2],
                                    [4.5, np.nan, 0.3, 0.4]], dtype=float))
        e_df = pd.DataFrame(np.array([[9.1, -3.9, 0.3, -0.3],
                                    [0.25, 0, -0.2, 0],
                                    [4.1, np.nan, -0.1, 0]], dtype=float))
        out_df = dry.row_median_normalize(df)
        self.assertTrue(np.allclose(out_df, e_df, atol=1e-2, equal_nan=True),
                        ("\nExpected out_df:\n{} " +
                         "\nActual out_df:\n{}").format(e_df, out_df))

    def test_subset_normalize(self):
        ROW_SUBSET_FIELD = "pr_probe_normalization_group"
        COL_SUBSET_FIELD = "det_normalization_group_vector"
        row_df = pd.DataFrame(np.array([["8350", "1"], ["8350", "1"],
                                        ["8350", "2"], ["8350", "2"]]),
                              index=["r1", "r2", "r3", "r4"],
                              columns=["pr_gene_id", "pr_probe_normalization_group"])
        col_df = pd.DataFrame(np.array([["G-0022", "1,1"], ["G-0022", "1,1"], ["G-0022", "1,2"],
                                        ["G-0022", "2,2"], ["G-0022", "2,2"]]),
                              index=["c1", "c2", "c3", "c4", "c5"],
                              columns=["det_plate", "det_normalization_group_vector"])
        data_df = pd.DataFrame([[7, 8, 3, 8, 9],
                                [9, 7, 4, 9, 2],
                                [8, 6, 7, 8, 2],
                                [4, 8, 5, 5, 7]],
                               index=["r1", "r2", "r3", "r4"],
                               columns=["c1", "c2", "c3", "c4", "c5"],
                               dtype=float)
        in_gct = GCToo.GCToo.GCToo(data_df=data_df, row_metadata_df=row_df, col_metadata_df=col_df)
        e_df = pd.DataFrame(np.array([[0, 1, -4, -0.5, 0.5],
                                      [2, 0, -3, 3.5, -3.5],
                                      [1, -1, 0, 1, -5],
                                      [-2, 2, 0, 0, 2]], dtype=float))
        out_gct = dry.subset_normalize(in_gct, ROW_SUBSET_FIELD, COL_SUBSET_FIELD)
        self.assertTrue(np.array_equal(out_gct.data_df, e_df),
                        ("\nExpected out:\n{} " +
                         "\nActual out:\n{}").format(e_df, out_gct.data_df))

    def test_make_norm_ndarray(self):
        ROW_SUBSET_FIELD = "pr_probe_normalization_group"
        COL_SUBSET_FIELD = "det_normalization_group_vector"
        row_df = pd.DataFrame(np.array([["8350", "1"], ["8350", "1"],
                                        ["8350", "2"], ["8350", "2"]]),
                              index=["r1", "r2", "r3", "r4"],
                              columns=["pr_gene_id", "pr_probe_normalization_group"])
        col_df = pd.DataFrame(np.array([["G-0022", "1,1"], ["G-0022", "1,1"], ["G-0022", "1,2"],
                                        ["G-0022", "2,2"], ["G-0022", "2,2"]]),
                              index=["c1", "c2", "c3", "c4", "c5"],
                              columns=["det_plate", "det_normalization_group_vector"])
        e_norm_ndarray = np.array([[1, 1, 1, 2, 2],
                                   [1, 1, 1, 2, 2],
                                   [1, 1, 2, 2, 2],
                                   [1, 1, 2, 2, 2]])
        norm_ndarray = dry.make_norm_ndarray(row_df, col_df, ROW_SUBSET_FIELD, COL_SUBSET_FIELD)
        self.assertTrue(np.array_equal(norm_ndarray, e_norm_ndarray),
                        ("\nExpected out:\n{} " +
                         "\nActual out:\n{}").format(e_norm_ndarray, norm_ndarray))

    def test_iterate_over_norm_ndarray_and_normalize(self):
        data_df = pd.DataFrame(np.array([[7, 8, 3, 8, 9],
                                         [9, 7, 4, 9, 2],
                                         [8, 6, 7, 8, 2],
                                         [4, 8, 5, 5, 7]]),
                                        index = ["a", "b", "c", "d"],
                                        dtype="float")
        norm_ndarray = np.array([[1, 1, 1, 2, 2],
                                 [1, 1, 1, 2, 2],
                                 [1, 1, 2, 2, 2],
                                 [1, 1, 2, 2, 2]])
        e_df = pd.DataFrame(np.array([[0, 1, -4, -0.5, 0.5],
                                      [2, 0, -3, 3.5, -3.5],
                                      [1, -1, 0, 1, -5],
                                      [-2, 2, 0, 0, 2]], dtype="float"))
        out_df = dry.iterate_over_norm_ndarray_and_normalize(data_df, norm_ndarray)
        self.assertTrue(np.array_equal(out_df, e_df),
                        ("\nExpected out:\n{} " +
                         "\nActual out:\n{}").format(e_df, out_df))

        # Slightly different norm_ndarray
        norm_ndarray = np.array([[1, 1, 1, 2, 2],
                                 [1, 1, 1, 2, 2],
                                 [1, 1, 2, 2, 3],
                                 [1, 1, 2, 2, 3]])
        e_df = pd.DataFrame(np.array([[0, 1, -4, -0.5, 0.5],
                                      [2, 0, -3, 3.5, -3.5],
                                      [1, -1, -0.5, 0.5, 0],
                                      [-2, 2, 0, 0, 0]], dtype="float"))
        out_df = dry.iterate_over_norm_ndarray_and_normalize(data_df, norm_ndarray)
        self.assertTrue(np.array_equal(out_df, e_df),
                        ("\nExpected out:\n{} " +
                         "\nActual out:\n{}").format(e_df, out_df))

        # Totally weird but acceptable norm_ndarray
        norm_ndarray = np.array([[2, 2, 3, 3, 3],
                                 [1, 1, 2, 2, 2],
                                 [-1, -1, -1, -1, -1],
                                 [1, 1, 0, 0, 0]])
        e_df = pd.DataFrame(np.array([[-0.5, 0.5, -5, 0, 1],
                                      [1, -1, 0, 5, -2],
                                      [1, -1, 0, 1, -5],
                                      [-2, 2, 0, 0, 2]], dtype="float"))
        out_df = dry.iterate_over_norm_ndarray_and_normalize(data_df, norm_ndarray)
        self.assertTrue(np.array_equal(out_df, e_df),
                        ("\nExpected out:\n{} " +
                         "\nActual out:\n{}").format(e_df, out_df))

    def test_insert_offsets_and_prov_code(self):
        data = pd.DataFrame([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]],
                            index=["a", "b", "c", "d"],
                            columns=["e", "f", "g"])
        row_meta = pd.DataFrame([["rm1", "rm2"],["rm3", "rm4"],["rm5", "rm6"],["rm7", "rm8"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_field1", "row_field2"])
        col_meta = pd.DataFrame([["cm1", "cm2"],["cm3", "cm4"],["cm5", "cm6"]],
                                index=["e", "f", "g"],
                                columns=["col_field1", "col_field2"])
        in_gct = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta, col_metadata_df=col_meta)
        offsets = np.array([3.0, 5.0, 8.0])
        offsets_field = "offsets"
        prov_code = ["A", "B", "C", "D"]
        prov_code_field = "col_field2"
        prov_code_delimiter = "+"
        e_col_meta = pd.DataFrame([["cm1", "A+B+C+D", 3.0],
                                   ["cm3", "A+B+C+D", 5.0],
                                   ["cm5", "A+B+C+D", 8.0]],
                                  index=["e", "f", "g"],
                                  columns=["col_field1", "col_field2", "offsets"])

        out_gct = dry.insert_offsets_and_prov_code(
            in_gct, offsets, offsets_field, prov_code, prov_code_field, prov_code_delimiter)

        self.assertTrue(np.array_equal(out_gct.col_metadata_df, e_col_meta))

    def test_configure_out_names(self):
        gct_path = "/cmap/location/somewhere/input.gct"
        out_name_from_args = "super_output.gct"
        out_pw_name_from_args = "super_duper.pw"

        # Using given args
        (out_gct_name, out_pw_name) = dry.configure_out_names(
            gct_path, out_name_from_args, out_pw_name_from_args)

        self.assertEqual(out_gct_name, out_name_from_args)
        self.assertEqual(out_pw_name, out_pw_name_from_args)

        # None provided
        (out_gct_name2, out_pw_name2) = dry.configure_out_names(
            gct_path, None, None)

        self.assertEqual(out_gct_name2, "input.gct.dry.processed.gct")
        self.assertEqual(out_pw_name2, "input.gct.dry.processed.pw")

    def test_write_output_pw(self):
        data = pd.DataFrame([[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]],
                            index=["a", "b"],
                            columns=["c", "d", "e", "f", "g"])
        row_meta = pd.DataFrame([["rm1", "rm2"],["rm3", "rm4"]],
                                index=["a", "b"],
                                columns=["row_field1", "row_field2"])
        col_meta = pd.DataFrame([["plate1", "A1"],["plate1", "A2"],["plate1", "A3"],
                                 ["plate1", "A4"], ["plate1", "A5"]],
                                index=["c", "d", "e", "f", "g"],
                                columns=["det_plate", "det_well"])
        in_gct = GCToo.GCToo.GCToo(data_df=data, row_metadata_df=row_meta, col_metadata_df=col_meta)

        post_sample_nan_remaining = ["c", "e", "f", "g"]
        post_sample_dist_remaining = ["c", "f", "g"]
        offsets = pd.Series([0.1, 5, 0.2, 0.3], index=["c", "e", "f", "g"])
        out_path = FUNCTIONAL_TESTS_DIR
        out_name = "test_write_output.pw"
        e_df = pd.DataFrame([["plate1", "A1", 0.1, True, True],
                             ["plate1", "A2", np.nan, False, False],
                             ["plate1", "A3", 5, False, True],
                             ["plate1", "A4", 0.2, True, True],
                             ["plate1", "A5", 0.3, True, True]],
                            columns=["plate_name", "well_name", "optimization_offset",
                                   "remains_after_outlier_removal", "remains_after_poor_coverage_filtration"])

        dry.write_output_pw(in_gct, post_sample_nan_remaining,
                            post_sample_dist_remaining, offsets, out_path, out_name)

        # Read back the pw file
        df_from_file = pd.read_csv(os.path.join(out_path, out_name), sep="\t")
        self.assertTrue(df_from_file.equals(e_df), (
            "\ndf_from_file:\n{}\ne_df:\n{}".format(df_from_file, e_df)))

        # Clean up
        if CLEANUP:
            os.remove(os.path.join(out_path, out_name))


    def test_slice_metadata_using_already_sliced_data_df(self):
        data = pd.DataFrame([[2, 3], [5, 6], [11, 12]],
                            index=["a", "b", "d"],
                            columns=["f", "g"])
        row_meta = pd.DataFrame([["rm1", "rm2"],["rm3", "rm4"],
                                 ["rm5", "rm6"],["rm7", "rm8"]],
                                index=["a", "b", "c", "d"],
                                columns=["row_field1", "row_field2"])
        col_meta = pd.DataFrame([["cm1", "cm2"],["cm3", "cm4"],["cm5", "cm6"]],
                                index=["e", "f", "g"],
                                columns=["col_field1", "col_field2"])
        e_row_meta = pd.DataFrame([["rm1", "rm2"],["rm3", "rm4"],["rm7", "rm8"]],
                                index=["a", "b", "d"],
                                columns=["row_field1", "row_field2"])
        e_col_meta = pd.DataFrame([["cm3", "cm4"],["cm5", "cm6"]],
                                index=["f", "g"],
                                columns=["col_field1", "col_field2"])

        out_gct = dry.slice_metadata_using_already_sliced_data_df(data, row_meta, col_meta)
        self.assertTrue(np.array_equal(out_gct.row_metadata_df, e_row_meta),
                        "row_metadata_df is wrong: \n{}".format(out_gct.row_metadata_df))
        self.assertTrue(np.array_equal(out_gct.col_metadata_df, e_col_meta),
                        "col_metadata_df is wrong: \n{}".format(out_gct.col_metadata_df))

    def test_calculate_offsets_analytically(self):
        # Case 1
        df = pd.DataFrame([[10, -3, 1.2],
                           [0.45, 0.2, np.nan],
                           [4.5, -4, 0.3]], dtype=float, columns=["b", "c", "a"])
        e_offsets = pd.Series([-4.375, 2.875, 0.0], index=["b", "c", "a"])
        offsets = dry.calculate_offsets_analytically(df)
        pd.util.testing.assert_series_equal(e_offsets, offsets)

        # Case 2
        df2 = pd.DataFrame([[1, 3, 7],
                           [2, 5, 11]], dtype=float, columns=["b", "c", "a"])
        e_offsets2 = pd.Series([2.5, 0, -5], index=["b", "c", "a"])
        offsets2 = dry.calculate_offsets_analytically(df2)
        pd.util.testing.assert_series_equal(e_offsets2, offsets2)


if __name__ == "__main__":
    setup_logger.setup(verbose=True)
    unittest.main()