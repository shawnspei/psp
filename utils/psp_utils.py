import logging
import utils.setup_logger as setup_logger
import ConfigParser
import os
import numpy as np
import pandas as pd
import in_out.parse_gctoo as parse_gctoo

# Setup logger
logger = logging.getLogger(setup_logger.LOGGER_NAME)


def read_gct_and_config_file(gct_path, config_path):
    """Read gct and config file.

    The config file has three sections: io, metadata, and parameters.
    These are returned as dictionaries. The field "nan_values" in "io" indicates
    what values to consider NaN when reading in the gct file. The fields
    "gcp_assays" and "p100_assays" are used to figure out if the given
    assay type is P100 or GCP.

    Args:
        gct_path (string): filepath to gct file
        config_path (string): filepath to config file

    Returns:
        gct (GCToo object)
        config_io (dictionary)
        config_metadata (dictionary)
        config_parameters (dictionary)
    """
    # Read config file
    config_parser = ConfigParser.RawConfigParser()
    config_parser.read(os.path.expanduser(config_path))

    # Return config fields as dictionarires
    config_io = dict(config_parser.items("io"))
    config_metadata = dict(config_parser.items("metadata"))
    config_parameters = dict(config_parser.items("parameters"))

    # Extract what values to consider NaN
    # N.B. eval used to convert string to list
    psp_nan_values = eval(config_io["nan_values"])

    # Parse the gct file and return GCToo object
    gct = parse_gctoo.parse(gct_path, nan_values=psp_nan_values)

    return gct, config_io, config_metadata, config_parameters


def extract_prov_code(col_meta_df, prov_code_field, prov_code_delim):
    """Extract the provenance code from the column metadata.

    It must be non-empty and the same for all samples.

    Args:
        col_meta_df (pandas df): contains provenance code metadata
        prov_code_field (string): name of metadata field for prov code
        prov_code_delim (string): string delimiter in prov code

    Returns:
        prov_code (list of strings)
    """
    # Create pandas series of all provenance codes
    prov_code_series = col_meta_df.loc[:, prov_code_field]

    # Split each provenance code string along the delimiter
    prov_code_list_series = prov_code_series.apply(lambda x: x.split(prov_code_delim))

    # Verify that all provenance codes are the same
    # (i.e. verify that all elements equal the first)
    all_same = True
    for prov_code_list in prov_code_list_series:
        all_same = (all_same and prov_code_list == prov_code_list_series[0])

    if all_same:
        prov_code = prov_code_list_series.iloc[0]
        assert prov_code != [""], "Provenance code is empty!"
        return prov_code

    else:
        err_msg = ("All columns should have the same provenance code, " +
                   "but actually np.unique(prov_code_list_series.values) = {}")
        logger.error(err_msg.format(np.unique(prov_code_list_series.values)))
        raise(Exception(err_msg.format(np.unique(prov_code_list_series.values))))