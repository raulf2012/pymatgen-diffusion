# coding: utf-8
# Copyright (c) Materials Virtual Lab.
# Distributed under the terms of the BSD License.

from __future__ import division, unicode_literals

from pymatgen.core import Structure
from pymatgen_diffusion.neb.pathfinder import IDPPSolver
import unittest
import numpy as np
import os

__author__ = "Iek-Heng Chu"
__version__ = "1.0"
__date__ = "March 14, 2017"

#test_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)))


def get_path(path_str, dirname="./"):
    cwd = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(cwd, dirname, path_str)
    return path


class IDPPSolverTest(unittest.TestCase):

    init_struct = Structure.from_file(get_path("CONTCAR-0",
                                               dirname="pathfinder_files"))
    final_struct = Structure.from_file(get_path("CONTCAR-1",
                                               dirname="pathfinder_files"))

    def test_idpp_from_ep(self):
        obj = IDPPSolver.from_endpoints([self.init_struct, self.final_struct],
                                        nimages=3, sort_tol=1.0)
        new_path = obj.run(maxiter=5000, tol=1e-5, gtol=1e-3, step_size=0.05,
                           max_disp=0.05, spring_const=5.0, species=["Li"])

        self.assertEqual(len(new_path), 5)
        self.assertEqual(new_path[1].num_sites, 111)
        self.assertTrue(np.allclose(new_path[0][2].frac_coords,
                                    np.array([0.50000014, 0.99999998, 0.74999964])))
        self.assertTrue(np.allclose(new_path[1][0].frac_coords,
                                    np.array([0.482439, 0.68264727, 0.26525066])))
        self.assertTrue(np.allclose(new_path[2][10].frac_coords,
                                    np.array([0.50113915, 0.74958704, 0.75147021])))
        self.assertTrue(np.allclose(new_path[3][22].frac_coords,
                                    np.array([0.28422885, 0.62568764, 0.98975444])))
        self.assertTrue(np.allclose(new_path[4][47].frac_coords,
                                    np.array([0.59767531, 0.12640952, 0.37745006])))

        pass

    def test_idpp(self):

        images = self.init_struct.interpolate(self.final_struct, nimages=4,
                                              autosort_tol=1.0)
        obj = IDPPSolver(images)
        new_path = obj.run(maxiter=5000, tol=1e-5, gtol=1e-3, step_size=0.05,
                           max_disp=0.05, spring_const=5.0, species=["Li"])

        self.assertEqual(len(new_path), 5)
        self.assertEqual(new_path[1].num_sites, 111)
        self.assertTrue(np.allclose(new_path[0][2].frac_coords,
                                    np.array([0.50000014, 0.99999998, 0.74999964])))
        self.assertTrue(np.allclose(new_path[1][0].frac_coords,
                                    np.array([0.482439, 0.68264727, 0.26525066])))
        self.assertTrue(np.allclose(new_path[4][47].frac_coords,
                                    np.array([0.59767531, 0.12640952, 0.37745006])))

        pass


if __name__ == '__main__':
    unittest.main()