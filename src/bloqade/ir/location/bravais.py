from pydantic.dataclasses import dataclass
from dataclasses import InitVar, fields
from typing import List, Tuple, Generator, Optional, Any
import numpy as np
import itertools
from numpy.typing import NDArray
from bloqade.ir.location.base import AtomArrangement, LocationInfo
from bloqade.ir import Scalar, cast


class Cell:
    def __init__(self, natoms: int, ndims: int) -> None:
        self.natoms = natoms
        self.ndims = ndims


@dataclass
class BoundedBravais(AtomArrangement):
    """Base classe for Bravais lattices
    [`AtomArrangement`][bloqade.ir.location.base.AtomArrangement].

    - [`Square`][bloqade.ir.location.bravais.Square]
    - [`Chain`][bloqade.ir.location.bravais.Chain]
    - [`Honeycomb`][bloqade.ir.location.bravais.Honeycomb]
    - [`Triangular`][bloqade.ir.location.bravais.Triangular]
    - [`Lieb`][bloqade.ir.location.bravais.Lieb]
    - [`Kagome`][bloqade.ir.location.bravais.Kagome]
    - [`Rectangular`][bloqade.ir.location.bravais.Rectangular]


    """

    shape: Tuple[int, ...]
    lattice_spacing: Scalar

    def __init__(self, *shape: int, lattice_spacing: Any = 1.0):
        super().__init__()
        self.shape = shape
        self.lattice_spacing = cast(lattice_spacing)
        self.__n_atoms = None
        self.__n_dims = None

    @property
    def n_atoms(self):
        """number of atoms

        Returns:
            int: number of atoms in the lattice

        """
        if not self.__n_atoms:
            self.__n_atoms = len(self.cell_atoms()) * np.prod(self.shape)
        return self.__n_atoms

    @property
    def n_dims(self):
        """dimension of the lattice

        Returns:
            int: dimension of the lattice

        """
        if not self.__n_dims:
            self.__n_dims = len(self.cell_vectors())
        return self.__n_dims

    def coordinates(self, index: List[int]) -> NDArray:
        """calculate the coordinates of a cell in the lattice
        given the cell index.
        """
        # damn! this is like stone age broadcasting
        vectors = np.array(self.cell_vectors())
        index = np.array(index)
        pos = np.sum(vectors.T * index, axis=1)
        return pos + np.array(self.cell_atoms())

    def enumerate(self) -> Generator[LocationInfo, None, None]:
        for index in itertools.product(*[range(n) for n in self.shape]):
            for pos in self.coordinates(index):
                position = tuple(self.lattice_spacing * pos)
                yield LocationInfo(position, True)

    def scale(self, factor: float | Scalar) -> "BoundedBravais":
        """Scale the current location with a factor.

        (x,y) -> factor*(x,y)

        Args:
            factor (float | Scalar): scale factor

        Returns:
            BoundedBravais: The lattice with the scaled locations
        """
        factor = cast(factor)
        obj = self.__new__(type(self))
        for f in fields(self):
            if f.name == "lattice_spacing":
                obj.lattice_spacing = factor * self.lattice_spacing
            else:
                setattr(obj, f.name, getattr(self, f.name))
        return obj


@dataclass
class Chain(BoundedBravais):
    """Chain lattice.

    - 1D lattice
    - primitive (cell) vector(s)
        - a1 = (1,0).
    - unit cell (1 atom(s))
        - loc (0,0)

    Args:
        L (int): number of sites in the chain
        lattice_spacing (Scalar, Real): lattice spacing. Defaults to 1.0.

    """

    def __init__(self, L: int, lattice_spacing: Any = 1.0):
        super().__init__(L, lattice_spacing=lattice_spacing)

    def cell_vectors(self) -> List[List[float]]:
        return [[1, 0]]

    def cell_atoms(self) -> List[List[float]]:
        return [[0, 0]]


@dataclass
class Square(BoundedBravais):
    """Square lattice.

    - 2D lattice
    - primitive (cell) vector(s)
        - a1 = (1,0)
        - a2 = (0,1)
    - unit cell (1 atom(s))
        - loc (0,0)

    Args:
        L (int): number of sites in linear direction. n_atoms = L * L.
        lattice_spacing (Scalar, Real): lattice spacing. Defaults to 1.0.

    """

    def __init__(self, L: int, lattice_spacing: Any = 1.0):
        super().__init__(L, L, lattice_spacing=lattice_spacing)

    def cell_vectors(self) -> List[List[float]]:
        return [[1, 0], [0, 1]]

    def cell_atoms(self) -> List[List[float]]:
        return [[0, 0]]


@dataclass(init=False)
class Rectangular(BoundedBravais):
    """Rectangular lattice.

    - 2D lattice
    - primitive (cell) vector(s)
        - a1 = (1,0)
        - a2 = (0,1)
    - unit cell (1 atom(s))
        - loc (0,0)


    Args:
        width (int): number of sites in x direction.
        height (int): number of sites in y direction.
        lattice_spacing_x (Scalar, Real):
            lattice spacing. Defaults to 1.0.
        lattice_spacing_y (Scalar, Real):
            lattice spacing in y direction. optional.

    """

    ratio: Scalar = 1.0
    lattice_spacing_x: InitVar[Any]
    lattice_spacing_y: InitVar[Any]

    def __init__(
        self,
        width: int,
        height: int,
        lattice_spacing_x: Any = 1.0,
        lattice_spacing_y: Optional[Any] = None,
    ):
        if lattice_spacing_y is None:
            self.ratio = cast(1.0) / cast(lattice_spacing_x)
        else:
            self.ratio = cast(lattice_spacing_y) / cast(lattice_spacing_x)

        super().__init__(width, height, lattice_spacing=lattice_spacing_x)

    def cell_vectors(self) -> List[List[float]]:
        return [[1, 0], [0, self.ratio]]

    def cell_atoms(self) -> List[List[float]]:
        return [[0, 0]]


@dataclass
class Honeycomb(BoundedBravais):
    """Honeycomb lattice.

    - 2D lattice
    - primitive (cell) vector(s)
        - a1 = (1, 0)
        - a2 = (1/2, sqrt(3)/2)
    - unit cell (2 atom(s))
        - loc1 (0, 0)
        - loc2 (1/2, 1/(2*sqrt(3))


    Args:
        L (int): number of sites in linear direction. n_atoms = L * L * 2.
        lattice_spacing (Scalar, Real):
            lattice spacing. Defaults to 1.0.

    """

    def __init__(self, L: int, lattice_spacing: Any = 1.0):
        super().__init__(L, L, lattice_spacing=lattice_spacing)

    def cell_vectors(self) -> List[List[float]]:
        return [[1.0, 0.0], [1 / 2, np.sqrt(3) / 2]]

    def cell_atoms(self) -> List[List[float]]:
        return [[0.0, 0.0], [1 / 2, 1 / (2 * np.sqrt(3))]]


@dataclass
class Triangular(BoundedBravais):
    """Triangular lattice.

    - 2D lattice
    - primitive (cell) vector(s)
        - a1 = (1, 0)
        - a2 = (1/2, sqrt(3)/2)
    - unit cell (1 atom(s))
        - loc (0, 0)


    Args:
        L (int): number of sites in linear direction. n_atoms = L * L.
        lattice_spacing (Scalar, Real):
            lattice spacing. Defaults to 1.0.

    """

    def __init__(self, L: int, lattice_spacing: Any = 1.0):
        super().__init__(L, L, lattice_spacing=lattice_spacing)

    def cell_vectors(self) -> List[List[float]]:
        return [[1.0, 0.0], [1 / 2, np.sqrt(3) / 2]]

    def cell_atoms(self) -> List[List[float]]:
        return [[0.0, 0.0]]


@dataclass
class Lieb(BoundedBravais):
    """Lieb lattice.

    - 2D lattice
    - primitive (cell) vector(s)
        - a1 = (1, 0)
        - a2 = (0, 1)
    - unit cell (3 atom(s))
        - loc1 (0, 0)
        - loc2 (0.5, 0)
        - loc3 (0 ,0.5)

    Args:
        L (int): number of sites in linear direction. n_atoms = L * L.
        lattice_spacing (Scalar, Real):
            lattice spacing. Defaults to 1.0.

    """

    def __init__(self, L: int, lattice_spacing: Any = 1.0):
        super().__init__(L, L, lattice_spacing=lattice_spacing)

    def cell_vectors(self) -> List[List[float]]:
        return [[1.0, 0.0], [0.0, 1.0]]

    def cell_atoms(self) -> List[List[float]]:
        return [[0.0, 0.0], [1 / 2, 0.0], [0.0, 1 / 2]]


@dataclass
class Kagome(BoundedBravais):
    """Kagome lattice.

    - 2D lattice
    - primitive (cell) vector(s)
        - a1 = (1, 0)
        - a2 = (1/2, sqrt(3)/2)
    - unit cell (3 atom(s))
        - loc1 (0, 0)
        - loc2 (0.5, 0)
        - loc3 (0.25 ,0.25sqrt(3))

    Args:
        L (int): number of sites in linear direction. n_atoms = L * L.
        lattice_spacing (Scalar, Real):
            lattice spacing. Defaults to 1.0.

    """

    def __init__(self, L: int, lattice_spacing: Any = 1.0):
        super().__init__(L, L, lattice_spacing=lattice_spacing)

    def cell_vectors(self) -> List[List[float]]:
        return [[1.0, 0.0], [1 / 2, np.sqrt(3) / 2]]

    def cell_atoms(self) -> List[List[float]]:
        return [[0.0, 0.0], [1 / 2, 0], [1 / 4, np.sqrt(3) / 4]]
