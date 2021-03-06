#!/usr/bin/env python3
#
# Does an average over boxes of the halo, galaxy and component
# power spectra.  For the component spectra it also replaces
# the low k parts of the noisiest spectra with PT.
#


import numpy as np
import glob
import os

from scipy.signal import savgol_filter as savgol


db    = "/global/cscratch1/sd/mwhite/LagEmu/AllSpectra/"
seeds = range(9200,9210)


def read_column(pattern,col):
    """Returns a numpy array of the column "col" of the files
       matching the pattern.  Return is of shape (nfile,ndata)."""
    flist = glob.glob(pattern)
    dd    = np.loadtxt(flist[0])
    ret   = np.zeros((len(flist),dd.shape[0]))
    for i,fn in enumerate(flist):
        ret[i,:] = np.loadtxt(fn,usecols=(col,))
    return(ret)
    #


def robust_avg(dd):
    """Works out a robust measure of the "location" for the data in "dd"
    Uses as score L=sqrt{1+x^2}-1 with x=(data-median)/MAD and
    minimizes \sum_i L(x_i-mu) for mu."""
    avg = np.mean(dd,axis=0)
    med = np.median(dd,axis=0)
    mad = np.median(np.abs(dd-med),axis=0)/0.68 + 1e-30
    xs  = np.empty_like(dd)
    for i in range(dd.shape[0]):
        xs[i,:]  = (dd[i,:]-med) / mad
    res = np.zeros_like(med)
    sig = np.zeros_like(med)
    for j in range(res.size):
        res[j] = np.mean(xs[:,j])
        mu,ss  = 0.0,0.0
        for iter in range(4):   # Newton-Raphson converges quickly.
            xv = xs[:,j]-mu
            rt = np.sqrt(1+xv**2)
            fv = np.sum( xv/rt )
            fp = np.sum( 1./rt**3 )
            mu = mu + fv/fp
            ss = mad[j]/np.sqrt(fp)
        res[j]=mu
        sig[j]=ss
    res = res * mad + med
    return((res,sig))
    #



def average_halo_spectra(lgMmin,lgMmax,zz):
    """Does the robust average of the halo spectra."""
    # First read the data, throwing away the first row (which is k=0).
    iz = int(100*zz+0.01)
    fn = db+"ph_{:05.2f}_{:05.2f}_z{:03d}_????.txt".format(lgMmin,lgMmax,iz)
    kk = read_column(fn,0)[0,1:]
    phh= read_column(fn,1)[:,1:]
    phm= read_column(fn,2)[:,1:]
    # Now we compute robust averages, which aren't really necessary
    # for the halos which are quite clean.
    mu_hh,sig_hh = robust_avg(phh)
    mu_hm,sig_hm = robust_avg(phm)
    # and write the summary file.
    fout=db+"ph_{:05.2f}_{:05.2f}_z{:03d}.txt".format(lgMmin,lgMmax,iz)
    ff  = open(fout,"w")
    ff.write("# Halo auto- and cross-power spectra.\n")
    ff.write("# Robust average of {:d} spectra using sqrt(1+x^2).\n".\
             format(phh.shape[0]))
    ff.write("# {:05.2f}<lgM<{:05.2f}, z={:.3f}\n".format(lgMmin,lgMmax,zz))
    ff.write("# {:>13s} {:>15s} {:>15s} {:>15s} {:>15s}\n".\
             format("k[h/Mpc]","<Phh>","Err[Phh]","<Phm>","Err[Phm]"))
    for i in range(kk.size):
        ff.write("{:15.5e} {:15.5e} {:15.5e} {:15.5e} {:15.5e}\n".\
                 format(kk[i],mu_hh[i],sig_hh[i],mu_hm[i],sig_hm[i]))
    ff.close()
    #





def average_galaxy_spectra(zz):
    """Does the robust average of the galaxy spectra."""
    # First read the data, throwing away the first row (which is k=0).
    iz = int(100*zz+0.01)
    fn = db+"pg_z{:03d}_????.txt".format(iz)
    kk = read_column(fn,0)[0,1:]
    phh= read_column(fn,1)[:,1:]
    phm= read_column(fn,2)[:,1:]
    # Now we compute robust averages, which aren't really necessary
    # for the galaxies which are quite clean.
    mu_hh,sig_hh = robust_avg(phh)
    mu_hm,sig_hm = robust_avg(phm)
    # and write the summary file.
    fout=db+"pg_z{:03d}.txt".format(iz)
    ff  = open(fout,"w")
    ff.write("# Galaxy (HOD) auto- and cross-power spectra.\n")
    ff.write("# Robust average of {:d} spectra using sqrt(1+x^2).\n".\
             format(phh.shape[0]))
    ff.write("# z={:.3f}\n".format(zz))
    ff.write("# {:>13s} {:>15s} {:>15s} {:>15s} {:>15s}\n".\
             format("k[h/Mpc]","<Phh>","Err[Phh]","<Phm>","Err[Phm]"))
    for i in range(kk.size):
        ff.write("{:15.5e} {:15.5e} {:15.5e} {:15.5e} {:15.5e}\n".\
                 format(kk[i],mu_hh[i],sig_hh[i],mu_hm[i],sig_hm[i]))
    ff.close()
    #







def average_component_spectra(zz):
    """Does the robust average of the component spectra."""
    # First read the data, throwing away the first row (which is k=0).
    iz = int(100*zz+0.01)
    fn = db+"pc_z{:03d}_R0_????.txt".format(iz)
    kk = read_column(fn,0)[0,1:]
    # Now we want to read in each of the remaining columns and average them.
    dd = np.loadtxt(db+"pc_z{:03d}_R0_{:04d}.txt".format(iz,seeds[1]))
    pk = np.zeros( (kk.size,dd.shape[1]) )
    pk[:,0] = kk
    # Now we compute robust averages, and here it matter more.
    for i in range(1,pk.shape[1]):
        dd     = read_column(fn,i)[:,1:]
        mu,sig = robust_avg(dd)
        pk[:,i]= mu.copy()
    # Some of the spectra are still a bit noisy, so we smooth them.
    for i in [3,4,7,8]:
        pk[:,i]= savgol(pk[:,i],7,polyorder=3)
    # and write the summary file.
    fout=db+"pc_z{:03d}_R0.txt".format(iz)
    ff  = open(fout,"w")
    ff.write("# LPT component spectra.\n")
    ff.write("# Robust average of {:d} spectra using sqrt(1+x^2).\n".\
             format(dd.shape[0]))
    ff.write("# z={:.3f}\n".format(zz))
    for i in range(kk.size):
        outstr = "{:15.5e}".format(kk[i])
        for j in range(1,pk.shape[1]):
            outstr += " {:15.5e}".format(pk[i,j])
        ff.write(outstr+"\n")
    ff.close()
    #







if __name__=="__main__":
    lgMmin = [12.0,12.5,13.0]
    lgMmax = [12.5,13.0,13.5]
    for i in range(len(lgMmin)):
        for zz in [0.0,0.5,1.0,2.0]:
            average_halo_spectra(lgMmin[i],lgMmax[i],zz)
    #
    for zz in [0.0,0.5,1.0,2.0]:
        average_component_spectra(zz)
    #
    for zz in [0.0,1.0]:
        average_galaxy_spectra(zz)
    #
