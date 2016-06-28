# coding: utf-8
# Copyright (c) Materials Virtual Lab.
# Distributed under the terms of the BSD License.

from __future__ import division, unicode_literals, print_function

__author__ = "Iek-Heng Chu"
__version__ = 1.0
__date__ = "04/15"

from collections import Counter
from scipy.stats import norm
import matplotlib.pyplot as plt
from pymatgen.util.plotting_utils import get_publication_quality_plot
from scipy import stats
import numpy as np


# TODO: add unittests, and ipython notebook examples


class VanHoveAnalysis(object):
    """
    Class for van Hove function analysis. In particular, self-part (Gs) and
    distinct-part (Gd) of the van Hove correlation function G(r,t)
    for given species and given structure are computed. If you use this class,
    please consider citing the following paper:

    Zhu, Z.; Chu, I.-H.; Deng, Z. and Ong, S. P. "Role of Na+ Interstitials
    and Dopants in Enhancing the Na+ Conductivity of the Cubic Na3PS4
    Superionic Conductor". Chem. Mater. (2015), 27, pp 8318–8325
    """

    def __init__(self, pmg_diff_analyzer, avg_nsteps=50, ngrid=101, rmax=10.0,
                 step_skip=50, sigma=0.1, species=["Li", "Na"]):
        """
        Initization.

        Args:
            pmg_diff_analyzer (DiffusionAnalyzer): A
                pymatgen.analysis.diffusion_analyzer.DiffusionAnalyzer object
            avg_nsteps (int): Number of t0 used for statistical average
            ngrid (int): Number of radial grid points
            rmax (float): Maximum of radial grid (the minimum is always set zero)
            step_skip (int): # of time steps skipped during analysis. It defines
                        the resolution of the reduced time grid
            sigma (float): Smearing of a Gaussian function
            species ([string]): a list of specie symbols of interest
        """

        # initial check
        if step_skip <= 0:
            raise ValueError("skip_step should be >=1!")

        nions, nsteps, ndim = pmg_diff_analyzer.disp.shape

        if nsteps <= avg_nsteps:
            raise ValueError("Number of timesteps is too small!")

        ntsteps = nsteps - avg_nsteps

        if ngrid - 1 <= 0:
            raise ValueError("Ntot should be greater than 1!")

        if sigma <= 0.0:
            raise ValueError("sigma should be > 0!")

        dr = rmax / (ngrid - 1)
        interval = np.linspace(0.0, rmax, ngrid)
        reduced_nt = int(ntsteps / float(step_skip)) + 1

        # reduced time grid
        rtgrid = np.arange(0.0, reduced_nt)
        # van Hove functions
        gsrt = np.zeros((reduced_nt, ngrid), dtype=np.double)
        gdrt = np.zeros((reduced_nt, ngrid), dtype=np.double)

        tracking_ions = []

        # auxiliary factor for 4*\pi*r^2
        aux_factor = 4.0 * np.pi * interval ** 2
        aux_factor[0] = np.pi * dr ** 2

        for i, ss in enumerate(pmg_diff_analyzer.get_drift_corrected_structures()):
            if i == 0:
                lattice = ss.lattice
                indices = [j for j, site in enumerate(ss) if
                           site.specie.symbol in species]
                rho = float(len(indices)) / ss.lattice.volume

            all_fcoords = np.array(ss.frac_coords)
            tracking_ions.append(all_fcoords[indices, :])

        tracking_ions = np.array(tracking_ions)

        gaussians = norm.pdf(interval[:, None], interval[None, :], sigma) / \
                    float(avg_nsteps) / float(len(indices))

        # calculate self part of van Hove function
        image = np.array([0, 0, 0])
        for it in range(reduced_nt):
            dns = Counter()
            it0 = min(it * step_skip, ntsteps)
            for it1 in range(avg_nsteps):
                dists = [lattice.get_distance_and_image(tracking_ions[it1][u],
                                                        tracking_ions[
                                                            it0 + it1][u],
                                                        jimage=image)[0] for u
                         in range(len(indices))]
                dists = filter(lambda e: e < rmax, dists)

                r_indices = [int(dist / dr) for dist in dists]
                dns.update(r_indices)

            for indx, dn in dns.most_common(ngrid):
                gsrt[it, :] += gaussians[indx, :] * dn

        # calculate distinct part of van Hove function of species
        r = np.arange(-1, 2)
        arange = r[:, None] * np.array([1, 0, 0])[None, :]
        brange = r[:, None] * np.array([0, 1, 0])[None, :]
        crange = r[:, None] * np.array([0, 0, 1])[None, :]
        images = arange[:, None, None] + brange[None, :, None] + crange[None,
                                                                 None, :]
        images = images.reshape((27, 3))

        # find the zero image vector
        zd = np.sum(images ** 2, axis=1)
        indx0 = np.argmin(zd)

        for it in range(reduced_nt):
            dns = Counter()
            it0 = min(it * step_skip, ntsteps)
            # print it + 1, reduced_nt

            for it1 in range(avg_nsteps):
                dcf = tracking_ions[it0 + it1, :, None, None, :] + images[None,
                                                                   None, :, :] \
                      - tracking_ions[it1, None, :, None, :]
                dcc = lattice.get_cartesian_coords(dcf)
                d2 = np.sum(dcc ** 2, axis=3)
                dists = [d2[u, v, j] ** 0.5 for u in range(len(indices)) for v
                         in range(len(indices)) \
                         for j in range(27) if u != v or j != indx0]
                dists = filter(lambda e: e < rmax, dists)

                r_indices = [int(dist / dr) for dist in dists]
                dns.update(r_indices)

            for indx, dn in dns.most_common(ngrid):
                gdrt[it, :] += gaussians[indx, :] * dn / aux_factor[indx] / rho

        self.obj = pmg_diff_analyzer
        self.avg_nsteps = avg_nsteps
        self.step_skip = step_skip
        self.rtgrid = rtgrid
        self.interval = interval
        self.gsrt = gsrt
        self.gdrt = gdrt

    def get_gs_plots(self, figsize=(12, 8)):
        """
        Plot self-part van Hove functions.
        """

        y = np.arange(np.shape(self.gsrt)[1]) * self.interval[-1] / float(
            len(self.interval) - 1)
        timeskip = self.obj.time_step * self.obj.step_skip
        x = np.arange(
                np.shape(self.gsrt)[0]) * self.step_skip * timeskip / 1000.0
        X, Y = np.meshgrid(x, y, indexing="ij")

        ticksize = int(figsize[0] * 2.5)

        plt.figure(figsize=figsize, facecolor="w")
        plt.xticks(fontsize=ticksize)
        plt.yticks(fontsize=ticksize)

        labelsize = int(figsize[0] * 3)

        plt.pcolor(X, Y, self.gsrt, cmap="jet", vmin=self.gsrt.min(), vmax=1.0)
        plt.xlabel("timesteps (ps)", size=labelsize)
        plt.ylabel("$r$ ($\AA$)", size=labelsize)
        plt.axis([x.min(), x.max(), y.min(), y.max()])

        cbar = plt.colorbar(ticks=[0, 1])
        cbar.set_label(label="4$\pi r^2G_s$($t$,$r$)", size=labelsize)
        cbar.ax.tick_params(labelsize=ticksize)
        plt.tight_layout()

        return plt

    def get_gd_plots(self, figsize=(12, 8)):
        """
        Plot distinct-part van Hove functions.
        """

        y = np.arange(np.shape(self.gdrt)[1]) * self.interval[-1] / float(
            len(self.interval) - 1)
        timeskip = self.obj.time_step * self.obj.step_skip
        x = np.arange(
                np.shape(self.gdrt)[0]) * self.step_skip * timeskip / 1000.0
        X, Y = np.meshgrid(x, y, indexing="ij")

        ticksize = int(figsize[0] * 2.5)

        plt.figure(figsize=figsize, facecolor="w")
        plt.xticks(fontsize=ticksize)
        plt.yticks(fontsize=ticksize)

        labelsize = int(figsize[0] * 3)

        plt.pcolor(X, Y, self.gdrt, cmap="jet", vmin=self.gdrt.min(), vmax=4.0)
        plt.xlabel("timesteps (ps)", size=labelsize)
        plt.ylabel("$r$ ($\AA$)", size=labelsize)
        plt.axis([x.min(), x.max(), y.min(), y.max()])
        cbar = plt.colorbar(ticks=[0, 1, 2, 3, 4])
        cbar.set_label(label="$G_d$($t$,$r$)", size=labelsize)
        cbar.ax.tick_params(labelsize=ticksize)
        plt.tight_layout()

        return plt

class RadialDistributionFunction(object):
    """
    Calculate the average radial distribution function for a given set of structures.
    """
    def __init__(self, pmg_structures, ngrid=101, rmax=10.0, cellrange=1, sigma=0.1,
                 species = ["Li","Na"]):
        """
        Args:
            pmg_structures (list of pmg_structure objects): List of structure objects with
                        the same composition. Allow for ensemble averaging.
            ngrid (int): Number of radial grid points.
            rmax (float): Maximum of radial grid (the minimum is always set zero).
            cellrange (int): Range of translational vector elements associated with supercell.
                            Default is 1, i.e. including the adjecent image cells along all three
                            directions.
            sigma (float): Smearing of a Gaussian function.
            species ([string]): A list of specie symbols of interest.
        """

        if ngrid - 1 <= 0:
            raise ValueError("Ntot should be greater than 1!")

        if sigma <= 0.0:
            raise ValueError("sigma should be > 0!")

        lattice = pmg_structures[0].lattice
        indices = [j for j, site in enumerate(pmg_structures[0]) if site.specie.symbol
                   in species]

        if len(indices) == 0:
            raise ValueError("Given species are not in the structure!")

        rho = float(len(indices)) / lattice.volume
        fcoords_list = []

        for s in pmg_structures:
            all_fcoords = np.array(s.frac_coords)
            fcoords_list.append(all_fcoords[indices,:])

        dr = rmax / (ngrid - 1)
        interval = np.linspace(0.0, rmax, ngrid)
        rdf = np.zeros((ngrid), dtype = np.double)
        dns = Counter()

        # generate the translational vectors
        r = np.arange(-cellrange, cellrange + 1)
        arange = r[:, None] * np.array([1, 0, 0])[None, :]
        brange = r[:, None] * np.array([0, 1, 0])[None, :]
        crange = r[:, None] * np.array([0, 0, 1])[None, :]
        images = arange[:, None, None] + brange[None, :, None] +crange[None, None, :]
        images = images.reshape((len(r)**3, 3))

        # find the zero image vector
        zd = np.sum(images**2, axis=1)
        indx0 = np.argmin(zd)

        for fcoords in fcoords_list:
            dcf = fcoords[:, None, None, :] + images[None, None, :, :] - fcoords[None, :, None, :]
            dcc = lattice.get_cartesian_coords(dcf)
            d2 = np.sum(dcc ** 2, axis=3)
            dists = [d2[u,v,j] ** 0.5 for u in range(len(indices)) for v in range(len(indices))
                     for j in range(len(r)**3) if u != v or j != indx0]
            dists = filter(lambda e: e < rmax + 1e-8, dists)
            r_indices = [int(dist / dr) for dist in dists]
            dns.update(r_indices)

        for indx, dn in dns.most_common(ngrid):
            if indx > len(interval) - 1: continue

            if indx == 0:
                ff = np.pi * dr ** 2
            else:
                ff = 4.0 * np.pi * interval[indx] ** 2

            rdf[:] += stats.norm.pdf(interval,interval[indx],sigma) * dn \
                    / float(len(indices)) / ff / rho / len(fcoords_list)

        self.structures = pmg_structures
        self.rdf = rdf
        self.interval = interval
        self.cellrange = cellrange
        self.rmax = rmax
        self.ngrid = ngrid
        self.species = species

    def get_rdf_plot(self, label=None, xlim=[0.0, 8.0], ylim=[-0.005, 3.0]):
        """
        Plot the average RDF function.
        """

        if label is None:
            symbol_list = set([e.symbol for e in self.structures[0].composition.keys()])
            symbol_list = list(symbol_list.intersection(set(self.species)))

            if len(symbol_list) == 1:
                label = symbol_list[0]
            else:
                label = "-".join(symbol_list)

        plt = get_publication_quality_plot(12,8)
        plt.plot(self.interval, self.rdf, color = "r", label=label, linewidth=4.0)
        plt.xlabel("$r$ ($\AA$)")
        plt.ylabel("$g(r)$")
        plt.legend(loc='upper right', fontsize=36)
        plt.xlim(xlim[0], xlim[1])
        plt.ylim(ylim[0], ylim[1])
        plt.tight_layout()

        return plt

    def export_rdf(self, filename):
        """
        Output RDF data to a csv file.

        Args:
            filename (str): Filename. Supported formats are csv and dat. If
                the extension is csv, a csv file is written. Otherwise,
                a dat format is assumed.
        """
        fmt = "csv" if filename.lower().endswith(".csv") else "dat"
        delimiter = ", " if fmt == "csv" else " "
        with open(filename, "wt") as f:
            if fmt == "dat":
                f.write("# ")
            f.write(delimiter.join(["r", "g(r)"]))
            f.write("\n")

            for r, gr in zip(self.interval, self.rdf):
                f.write(delimiter.join(["%s" % v for v in [r, gr]]))
                f.write("\n")