"""

These are sets of procedures optimised for almost empty fields 
but with extended line emission  

"""

def individual_resample(listob,refpath='./',nproc=24):

    """
    Loop over each OB and re-run scipost using a final coadded cube as
    a reference for WCS. This produces cubes that are all regridded to 
    a common 3D grid with a single interpolation. 


    listob -> OBs to process
    refpath -> where reference path is for WCS resampling
    nproc -> numer of processors in parallel runs 

    """
      
    import os
    import glob
    import subprocess
    import shutil
    from astropy.io import fits
    import muse_utils as mut 
    import numpy as np

    #grab top dir
    topdir=os.getcwd()

    #now loop over each folder and make the final sky-subtracted cubes
    for ob in listob:
        
        #change dir
        os.chdir(ob+'/Proc/')
        print('Processing {} for resampling on reference cube'.format(ob))
 
        #Search how many exposures are there
        scils=glob.glob("OBJECT_RED_0*.fits*")
        nsci=len(scils)

        #loop on exposures and reduce frame with sky subtraction 
        for exp in range(nsci):
            
            if not os.path.isfile('OFFSET_LIST_EXP{0:d}.fits'.format(exp+1)):
                print("Compute offsets...")
                            
                #create align file 
                alignsof=open('../Script/align_toref_{0:d}.sof'.format(exp+1),'w')
                alignsof.write("../../{}/IMAGE_FOV_0001.fits IMAGE_FOV\n".format(refpath))
                alignsof.write("IMAGE_FOV_EXP{0:d}.fits IMAGE_FOV\n".format(exp+1))
                alignsof.close()
                
                #run script align with respect to registered reference cube  
                alignscr=open('../Script/make_align_toref_{0:d}.sh'.format(exp+1),'w')
                alignscr.write("esorex --log-file=align_toref_{0:d}.log muse_exp_align --threshold=4. ../Script/align_toref_{0:d}.sof".format(exp+1))
                alignscr.close()
                subprocess.call(["sh","../Script/make_align_toref_{0:d}.sh".format(exp+1)])    
                
                #copy the offsets 
                alig=fits.open('OFFSET_LIST.fits')
                alig.writeto('OFFSET_LIST_EXP{0:d}.fits'.format(exp+1),clobber=True)

            else:
                print('Offsets exist.. skip')

            #define some output names for final cube 
            cname="DATACUBE_FINAL_LINEWCS_EXP{0:d}.fits".format(exp+1)
            pname="PIXTABLE_REDUCED_LINEWCS_EXP{0:d}.fits".format(exp+1)
            iname="IMAGE_FOV_LINEWCS_EXP{0:d}.fits".format(exp+1)
 
            if not os.path.isfile(cname):
                print("Processing exposure {0:d} to align to reference".format(exp+1))
                
                #copy sof file written for basic reduction
                sof_old=open("../Script/scipost_{0:d}.sof".format(exp+1))
                sof_name="../Script/scipost_line_{0:d}.sof".format(exp+1)
                sofedit=open(sof_name,'w')
                
                #read the offsets 
                alig=fits.open('OFFSET_LIST_EXP{0:d}.fits'.format(exp+1))
                offsets=alig[1].data[1]

                #now apply offsets to pixel table
                print ('Apply offsets...')
                pixtablist=[]
                for ll in sof_old:
                    if('PIXTABLE_OBJECT' in ll):
                        pixtab=ll.split(' ')[0]
                        pxt=fits.open(pixtab)
                        pxt[0].header['RA']=pxt[0].header['RA']-offsets[2]
                        pxt[0].header['DEC']=pxt[0].header['DEC']-offsets[3]
                        
                        pxt.writeto("WCS_"+pixtab,clobber=True)
                        pixtablist.append("WCS_"+pixtab)
                        sofedit.write("WCS_"+pixtab+" PIXTABLE_OBJECT\n")
                    else:
                        sofedit.write(ll)
                        
                #append reference frame to sof file 
                sofedit.write('../../{}/DATACUBE_FINAL.fits OUTPUT_WCS\n'.format(refpath))
                sofedit.close()
                sof_old.close()
                
                #Write the command file 
                scr=open("../Script/make_scipost_line_{0:d}.sh".format(exp+1),"w")
                scr.write("OMP_NUM_THREADS={0:d}\n".format(nproc)) 
                
                scr.write('esorex --log-file=scipost_line_{0:d}.log muse_scipost --filter=white  --skymethod="none" --save=cube,individual ../Script/scipost_line_{0:d}.sof'.format(exp+1))
                scr.close()
                
                #Run pipeline 
                subprocess.call(["sh", "../Script/make_scipost_line_{0:d}.sh".format(exp+1)])    
                subprocess.call(["mv","DATACUBE_FINAL.fits",cname])
                subprocess.call(["mv","IMAGE_FOV_0001.fits",iname])
                subprocess.call(["mv","PIXTABLE_REDUCED_0001.fits",pname])
            else:
                print("Exposure {0:d} exists.. skip! ".format(exp+1))
     

        #clean dir for unwanted stuff...
        print ('Clean directory!')
        garbage=glob.glob("WCS_PIXTABLE_OBJECT*")
        for gg in garbage:
            os.remove(gg)

        #back to top
        os.chdir(topdir)



def make_ifumasks(listob,refpath='./',nproc=24):

    """
    Loop over each OB and run scipost_make_cube on the reduced pixel tables
    to produce a final IFU masks for the resampled cube 

    listob -> OBs to process
    refpath -> where reference path is for WCS resampling
    nproc -> numer of processors in parallel runs 

    """
      
    import os
    import glob
    import subprocess
    import shutil
    from astropy.io import fits
    import muse_utils as mut 
    import numpy as np

    #grab top dir
    topdir=os.getcwd()

    #now loop over each folder and make the final sky-subtracted cubes
    for ob in listob:
        
        #change dir
        os.chdir(ob+'/Proc/')
        print('Processing {} for IFU mask'.format(ob))
 
        #Search how many exposures are there
        scils=glob.glob("OBJECT_RED_0*.fits*")
        nsci=len(scils)

        #loop on exposures and reduce frame with sky subtraction 
        for exp in range(nsci):
            
            #define some output names for final cube 
            cname="DATACUBE_IFUMASK_LINEWCS_EXP{0:d}.fits".format(exp+1)
            iname="IMAGE_IFUMASK_LINEWCS_EXP{0:d}.fits".format(exp+1)
 
            if not os.path.isfile(cname):
                print("Processing exposure {0:d} to produce IFU mask".format(exp+1))
                
                #make a sof file 
                sof_name="../Script/scipost_ifumask_{0:d}.sof".format(exp+1)
                sofedit=open(sof_name,'w')
                                        
                #append reduced pixel table and reference frame to sof file 
                origpix='PIXTABLE_REDUCED_LINEWCS_EXP{0:d}.fits'.format(exp+1)
                newpix='IFUMASK_PIXTABLE_LINEWCS_EXP{0:d}.fits'.format(exp+1)

                sofedit.write(newpix+' PIXTABLE_OBJECT\n')
                sofedit.write('../../{}/DATACUBE_FINAL.fits OUTPUT_WCS\n'.format(refpath))
                sofedit.close()
            
                #Write the command file 
                scr=open("../Script/make_scipost_ifumask_{0:d}.sh".format(exp+1),"w")
                scr.write("OMP_NUM_THREADS={0:d}\n".format(nproc)) 
                
                scr.write('esorex --log-file=scipost_ifumask_{0:d}.log muse_scipost_make_cube --filter=white ../Script/scipost_ifumask_{0:d}.sof'.format(exp+1))
                scr.close()

                #create the IFU mask 
                #unpack ifu origin
                pxt=fits.open(origpix)
                ifu,islice=mut.unpack_pixtab(pxt[7].data)
                
                #loop over ifu
                for iff in range(24): 
                    #group slices in 4 stacks
                    for i in range(4):
                        imin=i*12+1
                        imax=(i+1)*12 
                        
                        #find pixels and set value to flag 
                        pixinside=np.where((islice >= imin) & (islice <= imax) & (ifu == (iff+1)))
                        pxt[4].data[pixinside] = (iff+1)*100.+i+1
                        
                    print 'Done with IFU:', iff+1

                #save updated
                pxt.writeto(newpix,clobber=True)
                pxt.close()

                #Run pipeline 
                subprocess.call(["sh", "../Script/make_scipost_ifumask_{0:d}.sh".format(exp+1)])    
                subprocess.call(["mv","DATACUBE_FINAL.fits",cname])
                subprocess.call(["mv","IMAGE_FOV_0001.fits",iname])
            else:
                print("IFU mask {0:d} exists.. skip! ".format(exp+1))
     
        #back to top
        os.chdir(topdir)

def make_illcorr(listob):

    """    
    Wrapper function for illumination correction

    """

    import os
    import glob
 
    #grab top dir
    topdir=os.getcwd()

    #define the bandwidth for illumination correction
    #bindwith of ~100 are found to be optimal 
    binwidth=100

    #now loop over each folder and make the final illcorrected cubes
    for ob in listob:
        
        #change dir
        os.chdir(ob+'/Proc/')
        print('Processing {} for illumination correction'.format(ob))
 
        #Search how many exposures are there
        scils=glob.glob("OBJECT_RED_0*.fits*")
        nsci=len(scils)

        #loop on exposures and reduce frame with sky subtraction 
        for exp in range(nsci):
           
            #do pass on IFUs
            print('First pass for exposure {}'.format(exp+1))           
            #these are the ifu masks
            ifumask_cname="DATACUBE_IFUMASK_LINEWCS_EXP{0:d}.fits".format(exp+1)
            ifumask_iname="IMAGE_IFUMASK_LINEWCS_EXP{0:d}.fits".format(exp+1)
            #these are the data cubes
            data_cname="DATACUBE_FINAL_LINEWCS_EXP{0:d}.fits".format(exp+1)
            data_iname="IMAGE_FOV_LINEWCS_EXP{0:d}.fits".format(exp+1)
            #go for IFU corrections in coarse wavelenght bins
            outcorr="ILLCORR_EXP{0:d}_ifu.fits".format(exp+1)
            outcorrnorm="ILLCORRNORM_EXP{0:d}_ifu.fits".format(exp+1)
            newcube="DATACUBE_FINAL_LINEWCS_EXP{0:d}_ILLCORR_ifu.fits".format(exp+1)
            newimage="IMAGE_FOV_LINEWCS_EXP{0:d}_ILLCORR_ifu.fits".format(exp+1)
            make_illcorr_ifu(ifumask_cname,ifumask_iname,data_cname,\
                                 data_iname,outcorr,outcorrnorm,newcube,newimage,binwidth)
            
            #do second pass on stack - just constant on white image 
            print('Second pass for exposure {}'.format(exp+1))  
            #these are the ifu masks
            ifumask_cname="DATACUBE_IFUMASK_LINEWCS_EXP{0:d}.fits".format(exp+1)
            ifumask_iname="IMAGE_IFUMASK_LINEWCS_EXP{0:d}.fits".format(exp+1)
            #these are the data cubes
            data_cname=newcube
            data_iname=newimage
          
            #go for stack corrections in coarse wavelenght bins
            outcorrnorm="ILLCORRNORM_EXP{0:d}_stack.fits".format(exp+1)
            newcube="DATACUBE_FINAL_LINEWCS_EXP{0:d}_ILLCORR_stack.fits".format(exp+1)
            newimage="IMAGE_FOV_LINEWCS_EXP{0:d}_ILLCORR_stack.fits".format(exp+1)
            masknative="MASK_EXP{0:d}_ILLCORR_native.fits".format(exp+1)
            maskedges="MASK_EXP{0:d}_ILLCORR_edges.fits".format(exp+1)
            outcorr="ILLCORR_EXP{0:d}_stack.fits".format(exp+1)
            make_illcorr_stack(ifumask_cname,ifumask_iname,data_cname,\
                                 data_iname,outcorr,newcube,newimage,masknative,maskedges)
            

        #back to top for next OB 
        os.chdir(topdir)
 

def make_illcorr_ifu(ifumask_cname,ifumask_iname,data_cname,data_iname,outcorr,outcorrnorm,newcube,
                     newimage,binwidth,debug=False):

    """

    Perform illumination correction on IFUs in wavelength bins 

    ifumask_cname,ifumask_iname  --> IFU mask cube and image names
    data_cname,data_iname        --> data cube and image names
    outcorr,outcorrnorm          --> correction save name
    newcube,newimage             --> data cube and image names for wave dep IFU corrections
    binwidth                     --> how big chuncks in z-direction used for computing illumination correction
    debug                        --> enable interactive displays 

    """
      
    import os
    import glob
    import subprocess
    import shutil
    from astropy.io import fits
    import muse_utils as mut 
    import numpy as np
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import scipy.signal as sgn
    from scipy.stats import sigmaclip
    from scipy import interpolate
    import sep

    #open the ifu mask to create a good mask 
    data=fits.open(data_cname)
    ifimask=fits.open(ifumask_iname)
    fovdata=fits.open(data_iname)
      
    #define geometry 
    nwave=data[1].header["NAXIS3"]
    nx=data[1].header["NAXIS1"]
    ny=data[1].header["NAXIS2"]
            
    #now flag the sources
    ifumsk=ifimask[1].data
    image=fovdata[1].data.byteswap().newbyteorder()
    bkg=sep.Background(image)
    bkg.subfrom(image)
    obj,segmap=sep.extract(image,3.*bkg.globalrms,minarea=10,segmentation_map=True)

    #manual reset segmap
    #reset=np.where(segmap==20)
    #segmap[reset]=0

    #make a corse illumination correction in wavelenght
    nbins=nwave/binwidth
    illcorse=np.zeros((nbins,24))
    illnorm=np.zeros((nbins,24))
    illsmoo=np.zeros((nbins,24))
    cbins=np.array(range(nbins))*binwidth+binwidth/2.

    #skip if already processed
    if not os.path.isfile(outcorr):

        if(debug):
            plt.imshow(image,origin='low')
            plt.title('Field')
            plt.show()
            plt.imshow(segmap,origin='low')
            plt.title('Source mask')            
            plt.show()
            plt.imshow(ifumsk,origin='low')
            plt.title('IFU mask')            
            plt.show()
            
        #pixels used
        usedpix=np.zeros((ny,nx))
        #loop over ifus 
        for iff in range(24):                     
            print ('Computing correction for IFU {}'.format(iff+1))
            #reconstruct id of pixels in this IFU 
            flagvalue = (iff+1)*100.
            #pick pixels in this group and without sources
            #these are x,y in 2D image 
            goodpx=np.nonzero(((ifimask[1].data == flagvalue+1) |
                              (ifimask[1].data == flagvalue+2) |
                              (ifimask[1].data == flagvalue+3) |
                              (ifimask[1].data == flagvalue+4)) & (segmap < 1))
            usedpix[goodpx]=1
                          
            #loop over bins
            for bb in range(nbins):
                #get the start end index
                wstart=bb*binwidth 
                wend=(bb+1)*binwidth
                #sum all in wave
                img=np.nansum(data[1].data[wstart:wend,:,:],axis=0)/binwidth
                #take median across spatial pixels 
                illcorse[bb,iff]=np.nanmedian(img[goodpx])
                
                #compute robust mean - nans already excluded [does not perform very well]
                #c,l,u=sigmaclip(img[goodpx],3.,3.)
                #illcorse[bb,iff]=c.mean()

        #save 
        hdu = fits.PrimaryHDU(illcorse)
        hdulist = fits.HDUList([hdu])
        hdulist.writeto(outcorr,clobber=True)

        if(debug):
            plt.imshow(usedpix,origin='low')
            plt.title('Pixels used for IFU correction')
            plt.show()
    
    else:
        print('Loading pre-computed corrections')
        illcorse=(fits.open(outcorr))[0].data
    
    #skip if already exists
    if not os.path.isfile(newcube):      
          
        #next go for ifus normalisation given median
        for iff in range(24):
            #normalise
            illnorm[:,iff]=illcorse[:,iff]/np.nanmedian(illcorse,axis=1)
            #remove small scales bumps - [does not work well for discontinuities]
            #illsmoo[:,iff]=sgn.savgol_filter(illnorm[:,iff],5,1)
            #best to linear interpolate 
            illsmoo[:,iff]=illnorm[:,iff]
            
            if(debug):
                plt.scatter(cbins,illnorm[:,iff])
                plt.plot(cbins,illsmoo[:,iff])
                plt.title("Corrections for IFU {}".format(iff+1))
                plt.show()
                
        #save corrections
        hdu1 = fits.PrimaryHDU(illnorm)
        hdu2 = fits.ImageHDU(illsmoo)
        hdulist = fits.HDUList([hdu1,hdu2])
        hdulist.writeto(outcorrnorm,clobber=True)
        
        #store old cube to check final normalisation 
        oldcube=np.copy(data[1].data)
        #now apply
        for iff in range(24):   
            print ('Correct IFUs {}'.format(iff+1))
            if(iff < 23):
                #first, interpolation along ifus
                x_current_ifu=(iff+1)*100.
                x_next_ifu=(iff+2)*100.
                #grab relevant pixels 
                goodpx=np.where((ifimask[1].data >=x_current_ifu) & (ifimask[1].data < x_next_ifu))
                fcurrent=interpolate.interp1d(cbins,illsmoo[:,iff],fill_value="extrapolate")
                fnext=interpolate.interp1d(cbins,illsmoo[:,iff+1],fill_value="extrapolate")
                #loop over wave and apply correction 
                for ww in range(nwave):
                    y_current=fcurrent(ww)
                    y_next=fnext(ww)
                    slope=((y_next-y_current)/(x_next_ifu-x_current_ifu))
                    correction=y_current+slope*(ifimask[1].data[goodpx]-x_current_ifu)
                    #apply correction to data
                    img=data[1].data[ww,:,:]
                    img[goodpx]=img[goodpx]/correction
                    data[1].data[ww,:,:]=img
                    #preserve SN
                    var=data[2].data[ww,:,:]
                    var[goodpx]=var[goodpx]/correction/correction
                    data[2].data[ww,:,:]=var
            else:
                #deal with last - simple correction with no interpolation 
                x_current_ifu=(iff+1)*100.
                goodpx=np.where((ifimask[1].data >=x_current_ifu))
                fcurrent=interpolate.interp1d(cbins,illsmoo[:,iff],fill_value="extrapolate")
                for ww in range(nwave):
                    #apply to data
                    img=data[1].data[ww,:,:]
                    img[goodpx]=img[goodpx]/fcurrent(ww)
                    data[1].data[ww,:,:]=img                                       
                    #preserve SN
                    var=data[2].data[ww,:,:]
                    var[goodpx]=var[goodpx]/fcurrent(ww)/fcurrent(ww)
                    data[2].data[ww,:,:]=var                                       
  
        #finally, check for normalisation 
        print ('Checking flux normalisation...')
        white_old=np.zeros((ny,nx))
        white_new=np.zeros((ny,nx))
        for xx in range(nx):
            for yy in range(ny):
                white_old[yy,xx]=np.nansum(oldcube[:,yy,xx])/nwave
                white_new[yy,xx]=np.nansum(data[1].data[:,yy,xx])/nwave
                  
        #renormalise on sky only 
        goodpx=np.where((segmap==0)&(np.isfinite(ifimask[1].data)))
        #oldcoeff=np.nanmedian(white_old[goodpx])
        #newcoeff=np.nanmedian(white_new[goodpx])
        #print ('Renormalise by {}'.format(oldcoeff/newcoeff))
        #data[1].data=data[1].data*oldcoeff/newcoeff
        #data[2].data=data[2].data*(oldcoeff/newcoeff)*(oldcoeff/newcoeff)
        
        renormcoeff=np.nanmedian(white_old[goodpx]/white_new[goodpx])
        print ('Renormalise by {}'.format(renormcoeff))
        data[1].data=data[1].data*renormcoeff
        data[2].data=data[2].data*renormcoeff*renormcoeff
        #save new cubes 
        data.writeto(newcube,clobber=True)
        
        #create white image
        print ('Creating final white image')
        white_new=np.zeros((ny,nx))
        for xx in range(nx):
            for yy in range(ny):
                white_new[yy,xx]=np.nansum(data[1].data[:,yy,xx])/nwave  

        #save image
        hdu1 = fits.PrimaryHDU([])
        hdu2 = fits.ImageHDU(white_new)
        hdu2.header=data[1].header
        hdulist = fits.HDUList([hdu1,hdu2])
        hdulist.writeto(newimage,clobber=True)

    else:
        print ("Exposure already corrected for IFU illumination... move to next")
        


def make_illcorr_stack(ifumask_cname,ifumask_iname,data_cname,data_iname,outcorr,
                       newcube,newimage,masknative,maskedges,debug=False):

    """

    Perform illumination correction on stacks on white image only 

    ifumask_cname,ifumask_iname  --> IFU mask cube and image names
    data_cname,data_iname        --> data cube and image names
    outcorr                      --> correction save name
    newcube,newimage             --> data cube and image names for white image stack corrections
    masknative                   --> in oputput, mask of native pixels which have not been interpolated
    maskedges                    --> in output, mask of stack edges
    debug                        --> enable interactive displays 
   
    """
      
    import os
    import glob
    import subprocess
    import shutil
    from astropy.io import fits
    import muse_utils as mut 
    import numpy as np
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import scipy.signal as sgn
    from scipy.stats import sigmaclip
    from scipy import interpolate
    import sep

    #open the ifu mask to create a good mask 
    data=fits.open(data_cname)
    ifimask=fits.open(ifumask_iname)
    fovdata=fits.open(data_iname)
      
    #define geometry 
    nwave=data[1].header["NAXIS3"]
    nx=data[1].header["NAXIS1"]
    ny=data[1].header["NAXIS2"]
            
    #now flag the sources
    ifumsk=ifimask[1].data
    image=fovdata[1].data.byteswap().newbyteorder()
    bkg=sep.Background(image)
    bkg.subfrom(image)
    obj,segmap=sep.extract(image,5.*bkg.globalrms,minarea=10,segmentation_map=True)

    #remove illumination patterns that can be selected as sources
    #by allowing very extended regions
    for ii,pp in enumerate(obj):
        if(pp['npix'] > 900):
            #print ii, pp['npix']
            pix=np.where(segmap == ii+1)
            segmap[pix]=0

    if not os.path.isfile(newcube):
        
        if(debug):
            plt.imshow(image,origin='low')
            plt.title('Field')
            plt.show()
            plt.imshow(segmap,origin='low')
            plt.title('Source mask')            
            plt.show()
            plt.imshow(ifumsk,origin='low')
            plt.title('IFU mask')            
            plt.show()
  

        #now compute individual corrections and also prepare maks of native pixels"
        #the step above removes any wave dependency
        #now apply a stack by stack correction computed on white image
        print('Computing correction for stacks on white image')
        masknoninterp=np.zeros((ny,nx))
        usedpix=np.zeros((ny,nx))
        #renormalise on sky only 
        goodpx=np.where((segmap==0) & (np.isfinite(ifimask[1].data)))
        medcoeff=np.nanmedian(fovdata[1].data[goodpx])

        #now compute individual on stacks corrections
        white_corrections=np.zeros((24,4))
        for iff in range(24):   
            for i in range(4):
                #reconstruct id of pixels in this IFU 
                flagvalue = (iff+1)*100.+i+1
                #pick pixels in this group and without sources
                #these are indexes in 2D image
                goodpx=np.where((ifimask[1].data == flagvalue)&(segmap==0))
                nonintpx=np.where((ifimask[1].data == flagvalue))
                usedpix[goodpx]=1
                masknoninterp[nonintpx]=1
                white_corrections[iff,i]=medcoeff/np.nanmedian(fovdata[1].data[goodpx])

        #some dispaly
        if(debug):
            plt.imshow(usedpix,origin='low')
            plt.title('Pixels used for stack white correction')
            plt.show()
            
            plt.imshow(masknoninterp,origin='low')
            plt.title('Pixels not interpolated')
            plt.show()
            
        #save products 
        hdu = fits.PrimaryHDU(white_corrections)
        hdulist = fits.HDUList([hdu])
        hdulist.writeto(outcorr,clobber=True)

        #save products 
        hdu = fits.PrimaryHDU(white_corrections)
        hdulist = fits.HDUList([hdu])
        hdulist.writeto(outcorr,clobber=True)
        #save image
        hdu1 = fits.PrimaryHDU([])
        hdu2 = fits.ImageHDU(masknoninterp)
        hdu2.header=data[1].header
        hdulist = fits.HDUList([hdu1,hdu2])
        hdulist.writeto(masknative,clobber=True)

        #next apply correction
        maskpixedge=np.zeros((ny,nx))

        #grab muse rotator for this exposure
        rotation=data[0].header["HIERARCH ESO INS DROT POSANG"] 
    
        for iff in range(24):  
            #this/next ifu pixel 
            thisifu=(iff+1)*100.
            nextifu=(iff+2)*100.
            for i in range(4):
                #reconstruct id of pixels in this/next stack 
                thisstack=(iff+1)*100.+i+1
                nextstack=(iff+1)*100.+i+2
                #pixels in this exact stack
                instack=np.where(ifimask[1].data==thisstack)
                #pixels in this IFUs (also interpolated)
                inifu=np.where((ifimask[1].data>=thisifu) & (ifimask[1].data<nextifu))
             
                #first find left-right edges of the stacks - this is dependent on rotation
                if((rotation == 0.) | (rotation == 180.) | (rotation == 360.)):
                    #find edges with buffer
                    left=np.min(instack[1])
                    right=np.max(instack[1])
                    bottom=np.min(inifu[0])
                    top=np.max(inifu[0])
                    maskpixedge[bottom:top,left+2:right-2]=1
                    
                    #apply without interpolation
                    #apply to data
                    data[1].data[:,bottom:top,left:right]=data[1].data[:,bottom:top,left:right]*white_corrections[iff,i]
                    #preserve SN
                    data[2].data[:,bottom:top,left:right]=data[2].data[:,bottom:top,left:right]*\
                        white_corrections[iff,i]*white_corrections[iff,i]

                elif((rotation == 90.) | (rotation == 270.)):
                    left=np.min(instack[0])
                    right=np.max(instack[0])
                    bottom=np.min(inifu[1])
                    top=np.max(inifu[1])
                    maskpixedge[left+2:right-2,bottom:top]=1
       
                    #apply without interpolation
                    #apply to data
                    data[1].data[:,left:right,bottom:top]=data[1].data[:,left:right,bottom:top]*white_corrections[iff,i]
                    #preserve SN
                    data[2].data[:,left:right,bottom:top]=data[2].data[:,left:right,bottom:top]*\
                        white_corrections[iff,i]*white_corrections[iff,i]


                else:
                    print("Cannot handle rotation {}... quit!".format(rotation))
                    exit()
               

        if(debug):
            plt.imshow(maskpixedge,origin='low')
            plt.title("Edge mask")
            plt.show()

        #save edge mask
        hdu1 = fits.PrimaryHDU([])
        hdu2 = fits.ImageHDU(maskpixedge)
        hdu2.header=data[1].header
        hdulist = fits.HDUList([hdu1,hdu2])
        hdulist.writeto(maskedges,clobber=True)

        #save new cubes 
        data.writeto(newcube,clobber=True)
        
        #create white image
        print ('Creating final white image')
        white_new=np.zeros((ny,nx))
        for xx in range(nx):
            for yy in range(ny):
                white_new[yy,xx]=np.nansum(data[1].data[:,yy,xx])/nwave  

        #save image
        hdu1 = fits.PrimaryHDU([])
        hdu2 = fits.ImageHDU(white_new)
        hdu2.header=data[1].header
        hdulist = fits.HDUList([hdu1,hdu2])
        hdulist.writeto(newimage,clobber=True)

    else:
        print ("Exposure already corrected... go to next")


        
def internalskysub(listob,skymask):

    """

    Perform sky-subtraction using pixels within the cube

    listob  -> OBs to loop on
    skymask -> if defined, use goodpixels in the mask for computing sky. Otherwise mask sources.

    """
    
    import os
    import glob
    from astropy.io import fits
    import numpy as np

    #grab top dir
    topdir=os.getcwd()

    #now loop over each folder and make the final illcorrected cubes
    for ob in listob:
        
        #change dir
        os.chdir(ob+'/Proc/')
        print('Processing {} for illumination correction'.format(ob))
 
        #Search how many exposures are there
        scils=glob.glob("OBJECT_RED_0*.fits*")
        nsci=len(scils)

        #loop on exposures and reduce frame with sky subtraction 
        for exp in range(nsci):
           
            #do pass on IFUs
            print('Skysubtraction of exposure {}'.format(exp+1))           
           
            #define names
            oldcube="DATACUBE_FINAL_LINEWCS_EXP{0:d}_ILLCORR_stack.fits".format(exp+1)
            oldimage="IMAGE_FOV_LINEWCS_EXP{0:d}_ILLCORR_stack.fits".format(exp+1)
            newcube="DATACUBE_FINAL_LINEWCS_EXP{0:d}_lineskysub.fits".format(exp+1)
            newimage="IMAGE_FOV_LINEWCS_EXP{0:d}_lineskysub.fits".format(exp+1)
            ifumask_iname="IMAGE_IFUMASK_LINEWCS_EXP{0:d}.fits".format(exp+1)

            #open the cube 
            cube=fits.open(oldcube)

            #open mask ifu
            ifumask=fits.open(ifumask_iname)
  
            #define geometry 
            nwave=cube[1].header["NAXIS3"]
            nx=cube[1].header["NAXIS1"]
            ny=cube[1].header["NAXIS2"]
            
            #loop over ifu
            for iff in range(24):
                #loop over 
                #for i in range(4):
                #    #grab the pixels in this slice
                #    thisstack=(iff+1)*100.+i+1
                #    nextstack=(iff+1)*100.+i+2
                #    pixels=np.where((ifumask[1].data >= thisstack) & (ifumask[1].data < nextstack))
                 
                thisifu=(iff+1)*100.
                nextifu=(iff+2)*100.+1
                pixels=np.where((ifumask[1].data >= thisifu) & (ifumask[1].data < nextifu))
                
                #loop over wavelength 
                for ww in range(nwave):
                    skyimg=cube[1].data[ww,:,:]
                    medsky=np.nanmedian(skyimg[pixels])
                    skyimg[pixels]=skyimg[pixels]-medsky
                    cube[1].data[ww,:,:]=skyimg
                    
            #write final cube
            cube.writeto(newcube,clobber=True)
            
            #create white image
            print ('Creating final white image')
            white_new=np.zeros((ny,nx))
            for xx in range(nx):
                for yy in range(ny):
                    white_new[yy,xx]=np.nansum(cube[1].data[:,yy,xx])/nwave  
                    
            #save image
            hdu1 = fits.PrimaryHDU([])
            hdu2 = fits.ImageHDU(white_new)
            hdu2.header=cube[1].header
            hdulist = fits.HDUList([hdu1,hdu2])
            hdulist.writeto(newimage,clobber=True)

            
          
        #back to top for next OB 
        os.chdir(topdir)

    
