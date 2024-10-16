import numpy as np
import itertools
from .netSimPy import Link
from typing import List, Optional


#######################################################
# -------------------- ENV UTILS -------------------- #
#######################################################


def get_shared_link(path: List[Link], band: str):
    """Returns an array that represents the usage of the whole path
    Args:
        path (List[str]): _description_

    Returns:
        _type_: _description_
    """
    shared_link = [False] * min([link.getSlotsCount(band) for link in path])
    for link in path:
        for slotIndex in range(len(shared_link)):
            shared_link[slotIndex] = shared_link[slotIndex] or link.getSlotValue(
                slotIndex, band
            )
    return shared_link


def rle(inarray):
    """run length encoding. Partial credit to R rle function.
    Multi datatype arrays catered for including non Numpy
    returns: tuple (runlengths, startpositions, values)"""

    ia = np.asarray(inarray)  # force numpy
    n = len(ia)
    if n == 0:
        return (None, None, None)
    else:
        y = np.array(ia[1:] != ia[:-1])  # pairwise unequal (string safe)
        i = np.append(np.where(y), n - 1)  # must include last element posi
        z = np.diff(np.append(-1, i))  # run lengths
        p = np.cumsum(np.append(0, z))[:-1]  # positions
        return p, ia[i], z


def get_available_blocks(
    slots: int, path: List[Link], band: str, max_blocks: Optional[int] = None
):
    # getting available slots across the whole path
    # False if slot is available across all the links
    # True if not
    shared_link = get_shared_link(path, band)
    # getting the number of slots necessary for this service across this path
    # getting the blocks
    initial_indices, values, lengths = rle(shared_link)
    # selecting the indices where the block is available, i.e., equals to 0
    available_indices = np.where(values == False)

    # selecting the indices where the block has sufficient slots
    sufficient_indices = np.where(lengths >= slots)

    # getting the intersection, i.e., indices where the slots are available in sufficient
    # quantity and using as much max_blocks
    if max_blocks is not None:
        final_indices = np.intersect1d(available_indices, sufficient_indices)[:max_blocks]
    else:
        final_indices = np.intersect1d(available_indices, sufficient_indices)

    return initial_indices[final_indices], lengths[final_indices]


def pairwise(iterable):
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)