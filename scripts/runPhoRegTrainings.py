#!/usr/bin/env python3

import subprocess
import os
import regtools
from regtools import RegArgs
import argparse   

def main():
    
    parser = argparse.ArgumentParser(description='runs the photon regression trainings')
    parser.add_argument('--era',required=True,help='year to produce for; 2021Run3 is the only option')
    parser.add_argument('--input_dir','-i',default='/home/hep/wrtabb/Egamma/input_trees/Run3_2021',help='input directory with the ntuples')
    parser.add_argument('--output_dir','-o',default="results",help='output dir')
    args = parser.parse_args()

    #step 1, run calo only regression on the ideal IC to get the mean
    #step 2, apply the mean to the real IC sample and save the result in a tree
    #step 3, retrain the resolution for the real IC on the corrected energy

    #event split: ECAL Ideal IC train = eventnr%10=0
    #             ECAL Real IC train = eventnr%10=1
    run_step1 = True
    run_step2 = True
    run_step3 = True
    
    base_pho_cuts = "(mc.energy>0 && ssFrac.sigmaIEtaIEta>0 && ssFrac.sigmaIPhiIPhi>0 && pho.et>0 && pho.nrSatCrys==0 && {extra_cuts})"


    if args.era=='2021Run3':
        era_name = "2021Run3"
        input_ideal_ic  = "{}/DoublePhoton_FlatPt-5To500_FlatPU0to70IDEALGT_120X_mcRun3_2021_realistic_v6_ECALIdealIC-v2_AODSIM.root".format(args.input_dir)
        input_real_ic = "{}/DoublePhoton_FlatPt-5To500_FlatPU0to70_120X_mcRun3_2021_realistic_v6-v1_AODSIM.root".format(args.input_dir)
        ideal_eventnr_cut = "evt.eventnr%5==0"
        real_eventnr_cut = "evt.eventnr%5==1"
    elif args.era=='Run3_2023_UPC':
        era_name = "Run3_2023_UPC"
        input_ideal_ic  = "/eos/cms/store/group/phys_heavyions/anstahll/CERN/PbPb2023/NTUple/EGTree/EGTree_DoublePhoton_FlatPt0p5To50_IdealEcalIC_fwRec_MC_HIRun2023_2024_08_18.root"
        input_real_ic = "/eos/cms/store/group/phys_heavyions/anstahll/CERN/PbPb2023/NTUple/EGTree/EGTree_DoublePhoton_FlatPt0p5To50_RealEcalIC_fwRec_MC_HIRun2023_2024_08_18.root"
        ideal_eventnr_cut = "evt.eventnr%4==0"  #5million photons
        real_eventnr_cut = "evt.eventnr%4==1" #5million photons
    else:
        raise ValueError("era {} is invalid, only option for now is 2021Run3".format(era))


    #step1 train the calo only regression using IDEAL intercalibration constants
    print("starting step1")
    regArgs = RegArgs()
    regArgs.input_training = str(input_ideal_ic)
    regArgs.input_testing = str(input_ideal_ic)  
    regArgs.set_phoecal_default() 
    regArgs.cuts_name = "stdCuts"
    regArgs.cuts_base = base_pho_cuts.format(extra_cuts = ideal_eventnr_cut)
    regArgs.cfg_dir = "configs"
    regArgs.out_dir = args.output_dir+"/resultsPhoV1_"+era_name
    regArgs.ntrees = 1500  
    regArgs.base_name = "regPhoEcal{era_name}_IdealIC_IdealTraining".format(era_name=era_name)
    if run_step1: regArgs.run_eb_and_ee()
    
    #step2 now we run over the REAL intercalibration constant data and make a new tree with this regression included
    print("starting step2")
    regArgs.do_eb = True
    forest_eb_file = regArgs.output_name()
    regArgs.do_eb = False
    forest_ee_file = regArgs.output_name()

    regArgs.base_name = "regPhoEcal{era_name}_RealIC_IdealTraining".format(era_name=era_name)
    input_for_res_training = str(regArgs.applied_name()) #save the output name before we change it

    # Set scram arch
    arch = "el8_amd64_gcc11"
    if run_step2: subprocess.Popen(["bin/"+arch+"/RegressionApplierExe",input_real_ic,input_for_res_training,"--gbrForestFileEE",forest_ee_file,"--gbrForestFileEB",forest_eb_file,"--nrThreads","4","--treeName",regArgs.tree_name,"--writeFullTree","1","--regOutTag","Ideal"]).communicate()
    
    #step3 we now run over re-train with the REAL sample for the sigma, changing the target to have the correction applied 
    print("starting step3")
    regArgs.base_name = "regPhoEcal{era_name}_RealIC_RealTraining".format(era_name=era_name)
    regArgs.input_training = input_for_res_training
    regArgs.input_testing = input_for_res_training
    regArgs.target = "mc.energy/((sc.rawEnergy+sc.rawESEnergy)*regIdealMean)"
    regArgs.fix_mean = True
    regArgs.write_full_tree = "1"
    regArgs.reg_out_tag = "Real"
    regArgs.cuts_base = base_pho_cuts.format(extra_cuts = real_eventnr_cut)
    if run_step3: regArgs.run_eb_and_ee()

    
          
    
if __name__ =='__main__':
    main()


