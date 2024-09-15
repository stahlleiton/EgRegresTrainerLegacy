#!/usr/bin/env python3

import subprocess
import os
import regtools
from regtools import RegArgs
import argparse

def main():
    parser = argparse.ArgumentParser(description='runs the SC regression trainings')
    parser.add_argument('--era',required=True,help='regression to produce')
    # regression tags:
    # 2021Run3
    # HighEnergy
    parser.add_argument('--input_dir','-i',default='/home/hep/wrtabb/Egamma/input_trees/Run3_2021',help='input directory with the ntuples')
    parser.add_argument('--output_dir','-o',default="results",help='output dir')
    args = parser.parse_args()

    #step 1, run calo only regression on the ideal IC to get the mean
    #step 2, apply the mean to the real IC sample and save the result in a tree
    #step 3, retrain the resolution for the real IC on the corrected energy
    #step 4, run trk-calo regression using the real IC corrections as inputs 

    run_step1 = True 
    run_step2 = True
    run_step3 = True 
    run_step4 = True
    run_step4_extra = False
    
    base_ele_cuts = "(mc.energy>0 && ssFrac.sigmaIEtaIEta>0 && ssFrac.sigmaIPhiIPhi>0 && ele.et>0 && {extra_cuts})"

    if args.era=='2021Run3':
        era_name = "2021Run3"
        input_ideal_ic  = "{}/DoubleElectron_FlatPt-1To500_FlatPU0to70IDEALGT_120X_mcRun3_2021_realistic_v6_ECALIdealIC-v2_AODSIM.root".format(args.input_dir)
        input_real_ic  = "{}/DoubleElectron_FlatPt-1To500_FlatPU0to70_120X_mcRun3_2021_realistic_v6-v1_AODSIM.root".format(args.input_dir)
        ideal_eventnr_cut = "evt.eventnr%5==0"	# ~4 million electrons
        real_eventnr_cut = "evt.eventnr%5==1"	# ~4 million electrons
        ep_eventnr_cut = "evt.eventnr%5==2"	# ~4 million electrons
    elif args.era=='Run3_2023_UPC':
        era_name = "Run3_2023_UPC"
        input_ideal_ic  = "/eos/cms/store/group/phys_heavyions/anstahll/CERN/PbPb2023/NTUple/EGTree/OFFICIAL/EGTree_DoubleElectron_FlatPt0p5To50_IdealEcalIC_fwRec_Official_MC_HIRun2023_2024_09_12.root"
        input_real_ic = "/eos/cms/store/group/phys_heavyions/anstahll/CERN/PbPb2023/NTUple/EGTree/OFFICIAL/EGTree_DoubleElectron_FlatPt0p5To50_RealEcalIC_fwRec_Official_MC_HIRun2023_2024_09_12.root"
        ideal_eventnr_cut = "evt.eventnr%4==0"  #5million electrons
        real_eventnr_cut = "evt.eventnr%4==1" #5million electrons
        ep_eventnr_cut = "evt.eventnr%4==2" #5million electrons
    elif args.era=='Run3_2023_UPC_LowPtGsdEle':
        era_name = "Run3_2023_UPC_LowPtGsdEle"
        input_ideal_ic  = "/eos/cms/store/group/phys_heavyions/anstahll/CERN/PbPb2023/NTUple/EGTree/OFFICIAL/EGTree_LowPtGsfEle_DoubleElectron_FlatPt0p5To50_IdealEcalIC_fwRec_Official_MC_HIRun2023_2024_09_12.root"
        input_real_ic = "/eos/cms/store/group/phys_heavyions/anstahll/CERN/PbPb2023/NTUple/EGTree/OFFICIAL/EGTree_LowPtGsfEle_DoubleElectron_FlatPt0p5To50_RealEcalIC_fwRec_Official_MC_HIRun2023_2024_09_12.root"
        ideal_eventnr_cut = "evt.eventnr%4==0"  #5million electrons
        real_eventnr_cut = "evt.eventnr%4==1" #5million electrons
        ep_eventnr_cut = "evt.eventnr%4==2" #5million electrons
    else:
        raise ValueError("era {} is invalid, the only available option is 2021Run3".format(era))


    
    
    
    #step1 train the calo only regression using IDEAL intercalibration constants
    print("starting step1")
    regArgs = RegArgs()
    regArgs.input_training = str(input_ideal_ic)
    regArgs.input_testing = str(input_ideal_ic)  
    regArgs.set_ecal_default()
    regArgs.cuts_base = base_ele_cuts.format(extra_cuts = ideal_eventnr_cut)
    regArgs.cuts_name = "stdCuts"
    regArgs.cfg_dir = "configs"
    regArgs.out_dir = args.output_dir+"/resultsEleV1_"+era_name
    regArgs.ntrees = 1500  
    regArgs.base_name = "regEleEcal{era_name}_IdealIC_IdealTraining".format(era_name=era_name)
    if run_step1: regArgs.run_eb_and_ee()
    
    #step2 now we run over the REAL intercalibration constant data and make a rew tree with this regression included
    print("starting step2")
    regArgs.do_eb = True
    forest_eb_file = regArgs.output_name()
    regArgs.do_eb = False
    forest_ee_file = regArgs.output_name()

    regArgs.base_name = "regEleEcal{era_name}_RealIC_IdealTraining".format(era_name=era_name)
    input_for_res_training = str(regArgs.applied_name()) #save the output name before we change it

    # Set scram arch
    arch = "el8_amd64_gcc11"

    if run_step2: subprocess.Popen(["bin/"+arch+"/RegressionApplierExe",input_real_ic,input_for_res_training,"--gbrForestFileEE",forest_ee_file,"--gbrForestFileEB",forest_eb_file,"--nrThreads","4","--treeName",regArgs.tree_name,"--writeFullTree","1","--regOutTag","Ideal"]).communicate()
    
    #step3 we now run over re-train with the REAL sample for the sigma, changing the target to have the correction applied 
    print("starting step3")
    regArgs.base_name = "regEleEcal{era_name}_RealIC_RealTraining".format(era_name=era_name)
    regArgs.input_training = input_for_res_training
    regArgs.input_testing = input_for_res_training
    regArgs.target = "mc.energy/((sc.rawEnergy+sc.rawESEnergy)*regIdealMean)"
    regArgs.fix_mean = True
    regArgs.write_full_tree = "1"
    regArgs.reg_out_tag = "Real"
    regArgs.cuts_base = base_ele_cuts.format(extra_cuts = real_eventnr_cut)
    if run_step3: regArgs.run_eb_and_ee()

    
    #step4 do the E/p low combination
    #remember we use the Ideal Mean but Real Sigma (real mean is 1 by construction)
    print("starting step4")
    input_for_comb = str(regArgs.applied_name())

    regArgs.base_name = "regEleEcalTrk{era_name}_RealIC".format(era_name=era_name)
    regArgs.var_eb =":".join(["(sc.rawEnergy+sc.rawESEnergy)*regIdealMean","regRealSigma/regIdealMean","ele.trkPModeErr/ele.trkPMode","(sc.rawEnergy+sc.rawESEnergy)*regIdealMean/ele.trkPMode","ele.ecalDrivenSeed","ssFull.e3x3/sc.rawEnergy","ele.fbrem","ele.trkEtaMode","ele.trkPhiMode"])
    regArgs.var_ee =":".join(["(sc.rawEnergy+sc.rawESEnergy)*regIdealMean","regRealSigma/regIdealMean","ele.trkPModeErr/ele.trkPMode","(sc.rawEnergy+sc.rawESEnergy)*regIdealMean/ele.trkPMode","ele.ecalDrivenSeed","ssFull.e3x3/sc.rawEnergy","ele.fbrem","ele.trkEtaMode","ele.trkPhiMode"])
    regArgs.target = "(mc.energy * (ele.trkPModeErr*ele.trkPModeErr + (sc.rawEnergy+sc.rawESEnergy)*(sc.rawEnergy+sc.rawESEnergy)*regRealSigma*regRealSigma) / ( (sc.rawEnergy+sc.rawESEnergy)*regIdealMean*ele.trkPModeErr*ele.trkPModeErr + ele.trkPMode*(sc.rawEnergy+sc.rawESEnergy)*(sc.rawEnergy+sc.rawESEnergy)*regRealSigma*regRealSigma ))"
    regArgs.input_training = input_for_comb
    regArgs.input_testing = input_for_comb
    regArgs.write_full_tree = "1"
    regArgs.fix_mean = False
    regArgs.reg_out_tag = "EcalTrk"
    regArgs.cuts_base = base_ele_cuts.format(extra_cuts = ep_eventnr_cut)
    if run_step4: 
        regArgs.run_eb_and_ee()
    if run_step4_extra:
        #first run low pt
        regArgs.base_name = "regEleEcalTrkLowPt{era_name}_RealIC".format(era_name=era_name)
        regArgs.cuts_base = base_ele_cuts.format(extra_cuts = "{eventnr_cut} && mc.pt<50".format(eventnr_cut=ep_eventnr_cut))
        forest_eb,forest_ee = regArgs.forest_filenames()
        regArgs.run_eb_and_ee()

        #now run high pt
        regArgs.base_name = "regEleEcalTrkHighPt{era_name}_RealIC".format(era_name=era_name)
        regArgs.cuts_base = base_ele_cuts.format(extra_cuts = "{eventnr_cut} && mc.pt>=50 && mc.pt<200".format(eventnr_cut=ep_eventnr_cut))
        forest_eb_highpt,forest_ee_highpt = regArgs.forest_filenames()
        regArgs.run_eb_and_ee()

        regArgs.base_name = "regEleEcalTrkLowHighPt{era_name}_RealIC".format(era_name=era_name)
        subprocess.Popen(["bin/"+arch+"/RegressionApplierExe",regArgs.input_testing,regArgs.applied_name(),"--gbrForestFileEB",forest_eb,"--gbrForestFileEE",forest_ee,"--gbrForestFileEBHighEt",forest_eb_highpt,"--gbrForestFileEEHighEt",forest_ee_highpt,"--highEtThres","50.","--nrThreads","4","--treeName",regArgs.tree_name,"--writeFullTree","0"]).communicate()
    
        
    
if __name__ =='__main__':
    main()


