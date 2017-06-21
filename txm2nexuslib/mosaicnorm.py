#!/usr/bin/python

"""
(C) Copyright 2014 Marc Rosanes
The program is distributed under the terms of the 
GNU General Public License (or the Lesser GPL).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import numpy as np
import nxs
import sys
import struct
import os

class MosaicNormalize:

    def __init__(self, inputfile, ratio=1):
        #Note: FF is equivalent to brightfield 
    
        filename_nexus = inputfile        
        self.input_nexusfile = nxs.open(filename_nexus, 'r')

        outputfilehdf5 = inputfile.split('.')[0]+'_mosaicnorm'+'.hdf5'
        
        self.mosaicnorm = nxs.NXentry(name= "MosaicNormalized")
        self.mosaicnorm.save(outputfilehdf5, 'w5')
    
        self.ratio_exptimes = ratio
            
        # Mosaic images
        self.nFrames = 0                
        self.numrows = 0
        self.numcols = 0
        self.dim_imagesMosaic = (0, 0, 1)
        self.energies = list()

        # FF images
        self.nFramesFF = 1
        self.numrowsFF = 0
        self.numcolsFF = 0
        self.dim_imagesFF = (1, 1, 0)
        
        self.normalizedmosaic_singleimage = 0
        
        return


    def normalizeMosaic(self):

        self.input_nexusfile.opengroup('NXmosaic')

        #############################################    
        ## Retrieving important data from angles   ##
        #############################################
        self.input_nexusfile.opengroup('sample')
        try: 
            self.input_nexusfile.opendata('rotation_angle')
            self.angles = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.mosaicnorm['rotation_angle'] = self.angles[0]
            self.mosaicnorm['rotation_angle'].write()  
        except:
            print("\nAngles could NOT be extracted.\n")
            try:
                self.input_nexusfile.closedata()
            except:
                pass               
        self.input_nexusfile.closegroup()

        #### Opening group instrument ###############
        self.input_nexusfile.opengroup('instrument')
    
        #############################################    
        ## Retrieving important data from energies ##
        #############################################
        self.input_nexusfile.opengroup('source')
        try: 
            self.input_nexusfile.opendata('energy')
            self.energies = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.mosaicnorm['energy'] = self.energies[0]
            self.mosaicnorm['energy'].write()  
        except:
            print("\nEnergies could NOT be extracted.\n")
            try:
                self.input_nexusfile.closedata()
            except:
                pass
        self.input_nexusfile.closegroup()       
                
        ###########################################    
        ## Retrieving important data from sample ##
        ###########################################
        self.input_nexusfile.opengroup('sample')

        self.input_nexusfile.opendata('data')
        self.infoshape = self.input_nexusfile.getinfo()
        self.dim_imagesMosaic = (self.infoshape[0][0], self.infoshape[0][1]) 
        self.numrows = self.infoshape[0][0]
        self.numcols = self.infoshape[0][1]
        print("Dimensions mosaic: {0}".format(self.dim_imagesMosaic))
        self.input_nexusfile.closedata()
                
        self.input_nexusfile.closegroup()    
        
        
        ###########################################    
        ## Retrieving important data from FF     ##
        ###########################################
        self.input_nexusfile.opengroup('bright_field')
        
        self.input_nexusfile.opendata('data')
        self.infoshapeFF = self.input_nexusfile.getinfo()
        self.dim_imagesFF = (self.infoshapeFF[0][0], self.infoshapeFF[0][1]) 
        self.numrowsFF = self.infoshapeFF[0][0]
        self.numcolsFF = self.infoshapeFF[0][1]
        print("Dimensions FF: {0}".format(self.dim_imagesFF))
        self.input_nexusfile.closedata()
               
        self.input_nexusfile.closegroup() 
          
            

        ###########################################    
        ## Normalization                         ##
        ########################################### 
        
        rest_rows_mosaic_to_FF = float(self.numrows) % float(self.numrowsFF)
        rest_cols_mosaic_to_FF = float(self.numcols) % float(self.numcolsFF)
        
        if (rest_rows_mosaic_to_FF == 0.0 and rest_cols_mosaic_to_FF == 0.0):
        
            rel_rows_mosaic_to_FF = int(self.numrows / self.numrowsFF)
            rel_cols_mosaic_to_FF = int(self.numcols / self.numcolsFF)
        
            self.mosaicnorm['mosaic_normalized'] = nxs.NXfield(
                            name='mosaic_normalized', dtype='float32' , 
                            shape=[self.numrows, self.numcols])

            self.mosaicnorm['mosaic_normalized'].attrs[
                                                    'Pixel Rows'] = self.numrows    
            self.mosaicnorm['mosaic_normalized'].attrs[
                                                 'Pixel Columns'] = self.numcols
            self.mosaicnorm['mosaic_normalized'].write()    
               
               
            self.input_nexusfile.opengroup('bright_field')
            self.input_nexusfile.opendata('data')                
            FF_image = self.input_nexusfile.getslab(
                 [0, 0], [self.numrowsFF, self.numcolsFF])               
            #print(np.shape(FF_image))
            #print(len(FF_image[0])) 
            self.input_nexusfile.closedata()
            self.input_nexusfile.closegroup()                   
        
            self.input_nexusfile.opengroup('sample')
            self.input_nexusfile.opendata('data')   
            

            ###########################################    
            ## Normalization row by row              ##
            ########################################### 
            for numrow in range (0, self.numrows):

                individual_FF_row = list(FF_image[numrow%self.numrowsFF])
                collageFFrow = individual_FF_row * rel_cols_mosaic_to_FF 

                individual_mosaic_row = self.input_nexusfile.getslab(
                                [numrow, 0, 0], [1, self.numcols, 1])    
                

                ### Formula ###                
                numerator = np.array(individual_mosaic_row)
                numerator = numerator.astype(float)
                numerator = numerator[0,:,0]

                denominator = np.array(collageFFrow)
                denominator = denominator.astype(float)
                
                self.norm_mosaic_row = np.array(numerator / (
                        denominator * self.ratio_exptimes), dtype = np.float32) 
                
                slab_offset = [numrow, 0]
                imgdata = np.reshape(self.norm_mosaic_row, (1, self.numcols), order='A')
                
                
                self.mosaicnorm['mosaic_normalized'].put(
                imgdata, slab_offset, refresh=False)
                self.mosaicnorm['mosaic_normalized'].write()
                
                if (numrow % 200 == 0):
                    print('Row %d has been normalized' % numrow)
            
            self.input_nexusfile.closedata()
            self.input_nexusfile.closegroup()
            self.input_nexusfile.close()
            print('\nMosaic has been normalized using the FF image.\n')
            

        else:
            print("Normalization of Mosaic is not possible because the " +
                  "dimensions of the Mosaic image are not a multiple of the " + 
                  "FF dimensions.")
                 
                  
                  