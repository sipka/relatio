import warnings
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from utils import UsedRoles


def build_df(
    *,
    clustering_res,
    postproc_roles,
    statement_index,
    used_roles: UsedRoles,
    clustering_mask=True,
):
    series = []
    for role in used_roles.used:
        if role == "B-ARGM-NEG":
            serie = pd.Series(
                data=[statement.get(role) for statement in postproc_roles],
                dtype="boolean",
                name=role,
            )
        elif role == "B-ARGM-MOD":
            b_arg_mod_res = []
            b_arg_mod_index = []
            for i, statement in enumerate(postproc_roles):
                if statement.get(role) is not None:
                    _res = statement[role]
                    if len(_res) == 0:
                        warnings.warn(
                            f"No labels in statement {i}", RuntimeWarning,
                        )
                        continue
                    elif len(_res) > 1:
                        warnings.warn(
                            f"Multiple labels \n  labels[{role}]={_res} in statement {i}. First one is picked.",
                            RuntimeWarning,
                        )

                    b_arg_mod_index.append(i)
                    b_arg_mod_res.append(_res[0])
            serie = pd.Series(data=b_arg_mod_res, index=b_arg_mod_index, name=role)

        elif role in used_roles.embeddable:
            if role == 'B-V':
                data = []
                for statement in postproc_roles:
                    if role in statement:
                        if len(statement[role]) != 0:
                            data.append(' '.join(statement[role]))
                        else:
                            data.append(pd.NA)
                    else:
                        data.append(pd.NA)
                serie = pd.Series(
                    data=data,
                    name=role,
                )
            else:
                # Nullable integer
                _dtype = clustering_res[role].dtype.name.replace("ui", "UI")
                serie = pd.Series(
                    data=clustering_res[role],
                    index=statement_index[role],
                    dtype=_dtype,
                    name=role,
                )
                if clustering_mask is not True:
                    serie = serie[clustering_mask[role]]

        series.append(serie)

    return pd.concat(series, axis=1)


class CoOccurrence:
    def __init__(
        self,
        df,
        labels,
        used_roles: UsedRoles,
        display_order=("ARGO", "B-ARGM-MOD", "B-V", "B-ARGM-NEG", "ARG1", "ARG2"),
    ):
        self._df = df
        self._labels = labels
        self._used_roles = used_roles
        self._display_order = display_order

    @property
    def subset(self):
        return set(self._sublist)

    @property
    def display_order(self):
        return tuple(sorted(self._sublist, key=self._display_order.index))

    @property
    def normal_order(self):
        if "B-ARGM-MOD" in self._sublist or "B-ARGM-NEG" in self._sublist:
            res = tuple(self._sublist[: self._BV_index]) + (
                tuple(self._sublist[self._BV_index :]),
            )
        else:
            res = tuple(self._sublist)
        return res

    def _display(self, inp):
        new_order = [self._sublist.index(el) for el in self.display_order]
        res = [inp[el] for el in new_order]
        return type(inp)(res)

    @subset.setter
    def subset(self, roles_subset: Optional[Set[str]]):
        if roles_subset is None:
            roles_subset = set(self._used_roles.used)
        elif not set(roles_subset).issubset(self._used_roles.used):
            raise ValueError(f"{roles_subset} not in {self._used_roles.used}")
        sublist = [el for el in self._used_roles.used if el in roles_subset]
        self._sublist = sublist
        df = self._df.loc[:, self._sublist].dropna()

        tuples = list(df.itertuples(index=False, name=None))
        # Group verb and negation or modals into one tuple
        self._BV_index = self._sublist.index("B-V")
        if "B-ARGM-MOD" in self._sublist or "B-ARGM-NEG" in self._sublist:
            tuples = [
                tup[: self._BV_index] + (tup[self._BV_index :],) for tup in tuples
            ]
        self._tuples = tuples

    @property
    def narratives_counts(self):
        res = unique_counts(self._tuples)
        return {self._label_and_order_tuple(k): v for k, v in res.items()}

    @property
    def narratives_pmi(self):
        res = compute_pmi(self._tuples)
        return {self._label_and_order_tuple(k): v for k, v in res.items()}

    def _label_and_order_tuple(self, el):
        if self._BV_index != len(self._sublist) - 1:
            _el = el[: self._BV_index] + (el[self._BV_index])
        else:
            _el = el
        res = [
            self._labels[role][_el[i]][0]
            for i, role in enumerate(self._sublist[: self._BV_index + 1])
        ]
        if self._BV_index != len(self._sublist) - 1:
            res[self._BV_index] = (res[self._BV_index], *_el[self._BV_index + 1 :])

        # display is not taking into account the tuple in tuple structure
        if self._BV_index != len(self._sublist) - 1:
            res = res[:-1] + list(res[-1])
        res = tuple(res)
        return self._display(res)


def unique_counts(
    tuples: List[Tuple[Any]], descending: bool = True
) -> Dict[Tuple[Any], int]:
    """
    Count the unique elements of the List.
    
    Examples:
    >>> unique_counts([])
    {}
    >>> unique_counts([(),()])
    {(): 2}
    >>> unique_counts([(1,None),(1,None),(1,2)])
    {(1, None): 2, (1, 2): 1}
    """
    res = dict(Counter(tuples))
    if descending:
        res = {k: v for k, v in sorted(res.items(), key=lambda item: -item[1])}
    return res


def unique_tuple_values_counts(tuples: List[Tuple[Any]]) -> List[Dict[Any, int]]:
    """
    Count the unique elements of the tuples inside the list on the same position.

    Examples:
    >>> unique_tuple_values_counts([])
    []
    >>> unique_tuple_values_counts([(),()])
    []
    >>> unique_tuple_values_counts([(1,None),(1,None),(1,2)])
    [{1: 3}, {None: 2, 2: 1}]
    """
    res: List[Dict[Any, int]] = []
    if not tuples:
        return res

    for i in range(0, len(tuples[0])):
        res.append(dict(Counter([t[i] for t in tuples])))
    return res


def compute_pmi(
    tuples: List[Tuple[Any]], descending: bool = True
) -> Dict[Tuple[Any], float]:
    if not tuples:
        return {}
    counts_narratives = unique_counts(tuples)
    counts_individual = unique_tuple_values_counts(tuples)

    results_dic = {}
    for t in counts_narratives:
        frequency_narrative = counts_narratives[t]
        product = 1
        for j in range(0, len(counts_individual)):
            product = product * counts_individual[j][t[j]]
        pmi = np.log(frequency_narrative / product)
        results_dic[t] = pmi

    if descending:
        results_dic = {
            k: v for k, v in sorted(results_dic.items(), key=lambda item: -item[1])
        }
    return results_dic
