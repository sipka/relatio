from typing import Dict, List, NamedTuple, Optional, Tuple
import numpy as np
from copy import deepcopy

def is_subsequence(
    v2: list, 
    v1: list
) -> bool:
    """
    
    Check whether v2 is a subsequence of v1.
    
    Args:
        v2/v1: lists of elements
        
    Returns:
        a boolean
    
    Example:
        >>> v1 = ['the', 'united', 'states', 'of', 'america']\n
        ... v2 = ['united', 'states', 'of', 'europe']\n
        ... is_subsequence(v2,v1)
        False
    
    """
    it = iter(v1)
    return all(c in it for c in v2) 


def mine_entities(
    statements: List[dict],
    entities: list,
    roles_index: Optional[int] = 0,
    entity_index: Optional[dict] = {},
    roles: Optional[List[str]] = ['ARGO', 'ARG1']
) -> Tuple[int, dict, List[dict]]:
    """
    
    A function that goes through statements and identifies pre-defined named entities within postprocessed semantic roles.
    
    Args:
        statements: list of dictionaries of postprocessed semantic roles
        entities: user-defined list of named entities 
        entity_index: a dictionary 
        roles_index: an integer to keep track of statements
        roles: a list of roles with named entities (default = ARG0 and ARG1)
        
    Returns:
        roles_index: updated index
        entity_index: updated dictionary
        roles_copy: new list of postprocessed semantic roles (without the named entities mined since they will not be embedded)
    
    """
    
    if entity_index == {}:
        entity_index = {role:{entity:np.asarray([], dtype=int) for entity in entities} for role in roles}
    
    roles_copy = deepcopy(statements)
    
    for i, statement in enumerate(statements):
        for role, tokens in statements[i].items():
            if role in roles:
                for entity in entities:
                    if is_subsequence(entity.split(), tokens)  == True: 
                        entity_index[role][entity] = np.append(entity_index[role][entity], [i + roles_index]) 
                        roles_copy[i][role] = []
                        
    roles_index = len(statements)
    
    return(roles_index, entity_index, roles_copy)