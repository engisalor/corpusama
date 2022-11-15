import pandas as pd

from datamgr.util import convert


def list_of_dict(ls: list):
    """Recursively converts a list of dicts to a dict of lists."""

    def _flatten(ls):
        if not isinstance(ls, list):
            return ls
        else:
            if dict not in [type(x) for x in ls]:
                return ls
            # for [dict, dict, nan] objects
            else:
                # convert nan to empty dict
                ls = [x if isinstance(x, dict) else {} for x in ls]
                # convert list of dicts to dict of lists
                dt = pd.DataFrame(ls).to_dict(orient="list")
                # continue with recursion if needed
                for k, v in dt.items():
                    dt[k] = _flatten(v)
                return dt

    return _flatten(ls)


def dataframe(df: pd.DataFrame, separator="__", reset_index=True):
    """Flattens a dataframe with list and dict objects, pops source columns.

    New column names are labelled by <source column name><separator><new key>."""

    # flatten data
    if reset_index:
        df.reset_index(drop=True, inplace=True)
    df = df.applymap(convert.str_to_obj)
    for col in df.columns:
        prefix = "".join([col, separator])
        df[col] = df[col].apply(list_of_dict)
        df = pd.concat([df, pd.json_normalize(df[col]).add_prefix(prefix)], axis=1)
    # drop original list of dict columns
    for col in df.columns:
        types = set([type(x) for x in df[col]])
        if dict in types:
            df.drop(col, inplace=True, axis=1)

    return df
