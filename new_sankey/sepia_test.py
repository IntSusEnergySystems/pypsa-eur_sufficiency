#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""


__version__ = "1.8"
__email__ = "adrien.jacob@negawatt.org"

import SEPIA_functions as sf # Custom functions
import SEPIA_additional_functions as saf # Custom functions
import pandas as pd # Read/analyse data
import datetime # For current time
import logging
import numpy as np
import yaml
import os

scenario = "suff"

ALL_COUNTRIES= ['AT', 'BE', 'BG', 'CH', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'NL', 'NO', 'PL', 'PT', 'SE', 'SI', 'SK', 'RO']

 # Import country data
COUNTRIES = pd.read_excel("COUNTRIES.xlsx", index_col=0)
 
options = pd.read_csv("costs.csv" ,index_col=[0, 1]).sort_index()

 # Import config data (nodes, processes, general settings etc.)
CONFIG = pd.read_excel("SEPIA_config.xlsx", ["MAIN_PARAMS","NODES","PROCESSES","PROCESSES_2","PROCESSES_3","IMPORT_MIX","INDICATORS","GAS_PRO","OIL_PRO"], index_col=0)

 # Main settings (cf. SEPIA_config for description of all setting constants)
MAIN_PARAMS = CONFIG["MAIN_PARAMS"].drop('Description',axis=1).to_dict()['Value']

NODES = CONFIG["NODES"]
FE_NODES = sf.nodes_by_type(NODES,'FINAL_ENERGIES')
SE_NODES = sf.nodes_by_type(NODES,'SECONDARY_ENERGIES')
PE_NODES = sf.nodes_by_type(NODES,'PRIMARY_ENERGIES')
DS_NODES = sf.nodes_by_type(NODES,'DEMAND_SECTORS')
II_NODES = sf.nodes_by_type(NODES,'IMPORTS')
EE_NODES = sf.nodes_by_type(NODES,'EXPORTS')
GHG_SECTORS = sf.nodes_by_type(NODES,'GHG_SECTORS')

PROCESSES = CONFIG["PROCESSES"].reset_index()
PROCESSES['Type'].fillna('', inplace=True)
PROCESSES_2 = CONFIG["PROCESSES_2"].reset_index()
PROCESSES_2['Type'].fillna('', inplace=True)
PROCESSES_3 = CONFIG["PROCESSES_3"].reset_index()
PROCESSES_3['Type'].fillna('', inplace=True)
INDICATORS = CONFIG["INDICATORS"]
LOCAL_GAS = CONFIG["GAS_PRO"]
LOCAL_GAS = LOCAL_GAS.drop('Unnamed: 5', axis=1)
LOCAL_OIL = CONFIG["OIL_PRO"]
LOCAL_OIL = LOCAL_OIL.drop('Unnamed: 5', axis=1)
 # Aggregated results per Country
tot_results = pd.DataFrame()
 # Dictionnaries storing results of the next section : "Country" => Value
tot_flows = {} # Energy flow DataFrames
tot_ghg = {}
tot_co2 = {}
total_country = 'EU'
include_total_country = True
if include_total_country == True:
     ALL_COUNTRIES.append(total_country)
else:
     ALL_COUNTRIES = ALL_COUNTRIES
 # Energy system (network graph) creation for all countries

print("\nEnergy system (network graph) creation\n")
print("ALL_COUNTRIES:", ALL_COUNTRIES)
 #print("snakemake.input.excelfile:", snakemake.input.excelfile)
 
for country in ALL_COUNTRIES:
    datafile = f"../results/{scenario}/sepia/inputs{country}.xlsx"
    
    '''load energy input data for Sepia'''
    data = pd.read_excel(datafile, sheet_name="Inputs", index_col=0, usecols="C:G")
    data.reset_index(drop=True, inplace=False)
    data=data.T
    
    
    # '''load co2 input data for Sepia'''
    # data_co2 = pd.read_excel(datafile, sheet_name="Inputs_co2", index_col=0, usecols="C:G")
    # data_co2.reset_index(drop=True, inplace=False)
    # data_co2=data_co2.T
    
    '''Remove any duplicated data'''
    data = data.loc[:,~data.columns.duplicated()] 
    # data_co2 = data_co2.loc[:,~data_co2.columns.duplicated()]# Remove duplicate indicators

    '''Consider the coding used in sepia config and put unfound demands from pypsa file to zero'''
    unfound_inputs = []
    unfound_inputs.extend(sf.unfound_indicators(data,PROCESSES,'Value_Code'))
    unfound_inputs.extend(sf.unfound_indicators(data,PROCESSES,'Efficiency_Code'))
    unfound_inputs.extend(sf.unfound_indicators(data,INDICATORS,'Value_Code'))
    if len(unfound_inputs)>0:
        data = data.reindex(columns=[*data.columns.tolist(), *unfound_inputs], fill_value=0)
        print("! Warning: the following indicators have not been found (they have been filled with 0): "+", ".join(unfound_inputs)+" !!!")
        
    # unfound_inputs_co2 = []
    # unfound_inputs_co2.extend(sf.unfound_indicators(data_co2,PROCESSES_2,'Value_Code'))
    # if len(unfound_inputs_co2)>0:
    #     data_co2 = data_co2.reindex(columns=[*data_co2.columns.tolist(), *unfound_inputs_co2], fill_value=0)
    #     print("! Warning: the following indicators have not been found (they have been filled with 0): "+", ".join(unfound_inputs_co2)+" !!!")

    # ## Corrections on input data
    # Renaming indicators, based on INDICATORS sheet
    data = data.rename(columns=dict(zip(INDICATORS['Value_Code'],INDICATORS.index)))
    data = data.loc[:,~data.columns.duplicated()] # Remove duplicate indicators
    # data_co2 = data_co2.rename(columns=dict(zip(INDICATORS['Value_Code'],INDICATORS.index)))
    # data_co2 = data_co2.loc[:,~data_co2.columns.duplicated()]
    # data_ghg = data_co2.copy()
    

    ## Creating flows filling values which do not require calculation, directly from input data
    proc_without_calc = PROCESSES[PROCESSES['Value_Code'].isin(data.columns)] # indicator is not empty and found in data
    flows = pd.DataFrame(data[proc_without_calc.Value_Code].values, index=data.index, columns=pd.MultiIndex.from_tuples(list(zip(proc_without_calc.Source, proc_without_calc.Target, proc_without_calc.Type)), names=('Source','Target','Type')))
    # proc_without_calc_co2 = PROCESSES_2[PROCESSES_2['Value_Code'].isin(data_co2.columns)] # indicator is not empty and found in data
    # flows_co2 = pd.DataFrame(data_co2[proc_without_calc_co2.Value_Code].values, index=data_co2.index, columns=pd.MultiIndex.from_tuples(list(zip(proc_without_calc_co2.Source, proc_without_calc_co2.Target, proc_without_calc_co2.Type)), names=('Source','Target','Type')))
    # proc_without_calc_ghg = PROCESSES_3[PROCESSES_3['Value_Code'].isin(data_ghg.columns)] # indicator is not empty and found in data
    # flows_ghg = pd.DataFrame(data_ghg[proc_without_calc_ghg.Value_Code].values, index=data_ghg.index, columns=pd.MultiIndex.from_tuples(list(zip(proc_without_calc_ghg.Source, proc_without_calc_ghg.Target, proc_without_calc_ghg.Type)), names=('Source','Target','Type')))
    
    '''Using JRC values for 2020 for Belgium'''
    # if country == 'BE':
    #    flows.loc['2020', ('ura_pe', 'elc_se', 'thm')] = 34.4
    #    flows.loc['2020', ('gaz_se', 'elc_se', 'thm')] = 35.7
    #    flows.loc['2020', ('eon_pe', 'elc_se', '')] = 8
    #    flows.loc['2020', ('eof_pe', 'elc_se', 'a')] = 2.8
    #    flows.loc['2020', ('eof_pe', 'elc_se', 'b')] = 1
    #    flows.loc['2020', ('eof_pe', 'elc_se', 'c')] = 1
    #    flows.loc['2020', ('spv_pe', 'elc_se', 'r')] = 5.1
    #    flows.loc['2020', ('enc_pe', 'elc_se', 'chp')] = 3
    for en_code in ['elc']:
        value_re_a = flows.loc['2020',('elc_fe','res','ea')].sum()
        value_re_b = flows.loc['2020',('elc_fe','res','eb')].sum()
        value_re_c = flows.loc['2020',('elc_fe','res','ec')].sum()
        value_re_d = flows.loc['2020',('elc_fe','res','ed')].sum()
        value_re_e = flows.loc['2020',('elc_fe','res','ee')].sum()
        value_re_f = flows.loc['2020',('elc_fe','res','ef')].sum()
        value_re_g = flows.loc['2020',('elc_fe','res','eg')].sum()
        value_re_h = flows.loc['2020',('elc_fe','res','eh')].sum()
        value_res_tot = value_re_a+value_re_b+value_re_c+value_re_d
        value_ter_tot = value_re_e+value_re_f+value_re_g+value_re_h
        value_res_elc = flows.loc['2020', ('elc_fe', 'res', 'elc')].sum()
        value_ter_elc = flows.loc['2020', ('elc_fe', 'res', '')].sum()
        flows.loc['2020', ('elc_fe', 'res', 'elc')] = value_res_elc - value_res_tot
        flows.loc['2020', ('elc_fe', 'res', '')] = value_ter_elc - value_ter_tot

    '''Attaching production from primary and secondary energies to final energy demands'''
    selected_columns = flows.columns.get_level_values('Source').isin(FE_NODES)
    fec_carrier = flows.loc[:, selected_columns]
    grouped_fec = fec_carrier.groupby(level='Source', axis=1).sum()
    fec = grouped_fec
    for en_code in ['vap','hyd','bev']:
        flows[(en_code+'_se',en_code+'_fe','')] = fec[en_code+'_fe']
    for en_code in ['elc']:
        flows[(en_code+'_se',en_code+'_fe','ed')] = fec[en_code+'_fe']
    for en_code in ['gaz']:
        flows[(en_code+'_se',en_code+'_fe','de')] = fec[en_code+'_fe']
    for en_code in ['pet']: 
      value_pet = fec[en_code+'_fe']
      value_fisch = flows[('hyd_se',  en_code + '_fe', '')].squeeze().rename_axis(None)
      pet_bm = flows[('enc_pe', en_code + '_fe', '')].squeeze().rename_axis(None)
      pet_elctr = flows[('enc_pe', en_code + '_fe', 'bio')].squeeze().rename_axis(None)
      tot_oil = (value_pet - value_fisch - pet_bm - pet_elctr).where(
              value_pet > (value_fisch + pet_bm + pet_elctr),
              value_fisch - pet_bm - value_pet)
      flows[(en_code + '_pe', en_code + '_fe', '')] = tot_oil
      
    for en_code in ['pet']: 
      value_pet = fec[en_code+'_fe']['2020']
      flows.loc['2020', (en_code + '_pe', en_code + '_fe', '')] = value_pet
    selected_columns_pe = flows.columns.get_level_values('Source').isin(FE_NODES)
    fec_carrier_pe = flows.loc[:, selected_columns_pe]
    grouped_fec_pe = fec_carrier_pe.groupby(level='Source', axis=1).sum()
    fec_pe = grouped_fec_pe
    for en_code in ['pac','enc','cms']:
        flows[(en_code+'_pe',en_code+'_fe','')] = fec_pe[en_code+'_fe']
  
    biogas_p = flows['bgl_pe','gaz_se',''].squeeze().rename_axis(None)
    biogas_cc = flows['bgl_pe','gaz_se','cc'].squeeze().rename_axis(None)
    biosng_p = flows['enc_pe','gaz_se',''].squeeze().rename_axis(None)
    meth_p = flows['hyd_se','gaz_se',''].squeeze().rename_axis(None)
   
        
    selected_columns_se = flows.columns.get_level_values('Source').isin(SE_NODES)
    fec_carrier_se = flows.loc[:, selected_columns_se]
    grouped_fec_se = fec_carrier_se.groupby(level='Source', axis=1).sum()
    fec_se = grouped_fec_se
    for en_code in ['gaz']:
        flows[(en_code+'_pe',en_code+'_se','')] = fec_se[en_code+'_se']-biogas_p-biosng_p-meth_p-biogas_cc
        
    
    sec_imports = flows.columns.get_level_values('Target').isin(SE_NODES)
    sec_imports = flows.loc[:, sec_imports]
    sec_imports = sec_imports.groupby(level='Target', axis=1).sum()
    if country != 'EU':
     for en_code in ['elc']:
        values_exp = sec_imports[en_code + '_se'] - fec_se[en_code + '_se']
        values_imp = fec_se[en_code + '_se'] - sec_imports[en_code + '_se']
        values_imp = values_imp.clip(lower=0)
        values_exp = values_exp.clip(lower=0)
        flows[('elec_imp',en_code + '_se', '')] = values_imp
        flows[(en_code+'_se','exp','')] = values_exp
     for en_code in ['hyd']:
        values_exp = sec_imports[en_code + '_se'] - fec_se[en_code + '_se']
        values_imp = fec_se[en_code + '_se'] - sec_imports[en_code + '_se']
        values_imp = values_imp.clip(lower=0)
        values_exp = values_exp.clip(lower=0)
        flows[('hyd_imp',en_code + '_se', '')] = values_imp
        flows[(en_code+'_se','exp','')] = values_exp
        
        
    other_imports = flows.columns.get_level_values('Target').isin(FE_NODES)
    other_imports = flows.loc[:, other_imports]
    other_imports = other_imports.groupby(level='Target', axis=1).sum() 
    if country != 'EU':
     for en_code in ['amm']:
        values_elec = flows[('elc_se',en_code + '_fe', '')].squeeze().rename_axis(None)
        flows[('met_fe','per', '')] = values_elec
        values_exp = other_imports[en_code + '_fe'] - fec_pe[en_code + '_fe'] - values_elec
        values_imp = fec_pe[en_code + '_fe'] - other_imports[en_code + '_fe'] - values_elec
        values_imp = values_imp.clip(lower=0)
        values_exp = values_exp.clip(lower=0)
        flows[('amm_imp',en_code + '_fe', '')] = values_imp
        flows[(en_code+'_fe','exp','')] = values_exp
     for en_code in ['met']:
        values_elec = flows[('elc_se',en_code + '_fe', '')].squeeze().rename_axis(None)
        flows[('met_fe','per', '')] = values_elec
        values_exp = other_imports[en_code + '_fe'] - fec_pe[en_code + '_fe'] - values_elec
        values_imp = fec_pe[en_code + '_fe'] - other_imports[en_code + '_fe'] - values_elec
        values_imp = values_imp.clip(lower=0)
        values_exp = values_exp.clip(lower=0)
        flows[('met_imp',en_code + '_fe', '')] = values_imp
        flows[(en_code+'_fe','exp','')] = values_exp
    else:
        values_elec = flows[('elc_se','met_fe', '')].squeeze().rename_axis(None)
        flows[('met_fe','per', '')] = values_elec
    # '''preparing co2 emissions for carbon sankey'''
    # tot_emm_s = flows_co2.columns.get_level_values('Source').isin(GHG_SECTORS)
    # tot_emm_s = flows_co2.loc[:, tot_emm_s]
    # tot_emm_s = tot_emm_s.groupby(level='Source', axis=1).sum() 
    
    # # '''using co2 intensities from pypsa and compuing it from demands as on pypsa they are solved on EU level'''
    # co2_intensity_gas = options.loc[("gas", "CO2 intensity"), "value"]
    # co2_intensity_met = options.loc[("methanolisation", "carbondioxide-input"), "value"]
  
    
    
    # tot_emm = flows_co2.columns.get_level_values('Target').isin(GHG_SECTORS)
    # tot_emm = flows_co2.loc[:, tot_emm]
    # tot_emm = tot_emm.groupby(level='Target', axis=1).sum() 
    # for en_code in ['net']:
    #     bm_cap = flows_co2[('atm', 'bec' + '_ghg', '')].squeeze().rename_axis(None)
    #     blg_cap = flows_co2[('atm', 'blg' + '_ghg', '')].squeeze().rename_axis(None)
    #     blg_cap_cc = flows_co2[('atm', 'blg' + '_ghg', 'cc')].squeeze().rename_axis(None)
    #     dac_cap = flows_co2[('atm', 'stm', '')].squeeze().rename_axis(None)
    #     bm_cap = bm_cap.sum(axis=1)
    #     values_atm = tot_emm['atm'] - tot_emm['bm_ghg'] - tot_emm['luf_ghg'] - bm_cap - dac_cap - blg_cap - blg_cap_cc
    #     flows_co2[('atm',en_code + '_ghg',  'net')] = values_atm
        
    # if country != 'EU':
    #  for en_code in ['met']:
    #   met_dem = fec_pe[en_code + '_fe']
    #   met_pro = flows[('hyd_se',en_code + '_fe', '')].squeeze().rename_axis(None)
    #   imp_met = (met_dem - met_pro) * co2_intensity_met 
    #   flows_co2[('hth_ghg',en_code + '_ghg', '')] = imp_met
    #   exp_met = (met_pro - met_dem) * co2_intensity_met
    #   flows_co2[(en_code + '_ghg',  'eth_ghg', '')] = exp_met
    
    # if country != 'EU':
    #  for en_code in ['gaz']:
    #     if (
    # (flows[('hyd_se', en_code + '_se',  '')].squeeze().rename_axis(None).sum() > 0) or
    # (flows[('bgl_pe', en_code + '_se',  'cc')].squeeze().rename_axis(None).sum() > 0)):
    #         tot_pro = biogas_p + biosng_p + meth_p + biogas_cc
    #         gas_dem = flows[(en_code + '_se', en_code + '_fe','de')].squeeze().rename_axis(None)
    #         gas_los = flows[(en_code + '_se', 'per','')].squeeze().rename_axis(None)
    #         if isinstance(gas_los, pd.DataFrame):
    #           gas_los = gas_los.sum(axis=1)
    #         gas_elc = flows[(en_code + '_se', 'elc_se', '')].squeeze().rename_axis(None)
    #         if isinstance(gas_elc, pd.DataFrame):
    #           gas_elc = gas_elc.sum(axis=1)
    #         gas_vap = flows[(en_code + '_se', 'vap_se', '')].squeeze().rename_axis(None)
    #         if isinstance(gas_vap, pd.DataFrame):
    #           gas_vap = gas_vap.sum(axis=1)
    #         gas_smr = flows[(en_code + '_se', 'hyd_se', 'smr')].squeeze().rename_axis(None)
    #         if isinstance(gas_smr, pd.DataFrame):
    #           gas_smr = gas_smr.sum(axis=1)
    #         tot_dem = gas_dem + gas_los + gas_elc + gas_vap + gas_smr
    #         exp_gas = tot_pro - tot_dem
    #         flows[(en_code + '_se', 'exp', '')] = exp_gas
    # for en_code in ['exg']:
    #     exp_emm = flows[('gaz' + '_se', 'exp', '')].squeeze().rename_axis(None) * co2_intensity_gas
    #     flows_co2[('gas_ghg',en_code + '_ghg', '')] = exp_emm
    
    
    for en_code in ['gaz']: 
      value_smr = flows.loc['2020', (en_code + '_se', 'hyd_se', 'smr')].sum() 
      flows.loc['2020', (en_code + '_se', 'hyd_fe', 'ddd')] = value_smr 
      flows.loc['2020', (en_code + '_se', 'hyd_se', 'smr')] = 0
      flows.loc['2020', ('hyd_se', 'hyd_fe', '')] = 0
      
    ''' Adding missing values for nuclear losses'''
    nuc_eff = options.loc[("nuclear", "efficiency"), "value"]
    nuc_los = (1 - nuc_eff)/nuc_eff
    for en_code in ['ura']:
      value_loss_nuc = flows.loc['2020', (en_code + '_pe', 'elc_se', 'thm')].sum() * nuc_los
      flows.loc['2020', (en_code + '_pe', 'per', 'thm')] = value_loss_nuc 
    ''' Adding missing values for CCGT, OCGT & Gas-CHP losses'''
    ccgt_eff = options.loc[("CCGT", "efficiency"), "value"]
    ocgt_eff = options.loc[("OCGT", "efficiency"), "value"]
    chp_eff = options.loc[("central gas CHP", "efficiency"), "value"]
    chp_cc_eff = options.loc[("central gas CHP CC", "efficiency"), "value"]
    ccgt_los = (1 - ccgt_eff)/ccgt_eff
    ocgt_los = (1 - ocgt_eff)/ocgt_eff
    chp_los = (1 - chp_eff)/chp_eff
    chp_cc_los = (1 - chp_cc_eff)/chp_cc_eff
    for en_code in ['gaz']:
      value_loss_ccgt = flows.loc['2020', (en_code + '_se', 'elc_se', 'thm')].sum() * ccgt_los
      flows.loc['2020', (en_code + '_se', 'per', 'thm')] = value_loss_ccgt 
      value_loss_ocgt = flows.loc['2020', (en_code + '_se', 'elc_se', '')].sum() * ocgt_los
      flows.loc['2020', (en_code + '_se', 'per', '')] = value_loss_ocgt
      value_loss_chp = flows.loc['2020', (en_code + '_se', 'elc_se', 'chp')].sum() * chp_los
      flows.loc['2020', (en_code + '_se', 'per', 'chp')] = value_loss_chp
      value_loss_chp_cc = flows.loc['2020', (en_code + '_se', 'elc_se', 'chpcc')].sum() * chp_cc_los
      flows.loc['2020', (en_code + '_se', 'per', 'chpcc')] = value_loss_chp_cc
      value_gas = flows.loc['2020', (en_code + '_pe', 'gaz_se', '')].sum()
      flows.loc['2020', (en_code + '_pe', 'gaz_se', '')] = value_gas + value_loss_ccgt + value_loss_ocgt + value_loss_chp + value_loss_chp_cc
      
    ''' Aggregating transmission grid losses on country level transmission lines assuming 1% losses'''
    # if country != 'EU':
    for en_code in ['elc']:
      value_elcct = flows.loc['2020',(en_code + '_se', en_code + '_fe','ed')].sum() * 0.99
      value_elcct_loss = flows.loc['2020',(en_code + '_se', en_code + '_fe','ed')].sum() * 0.01
      flows.loc['2020',(en_code+'_se',en_code+'_fe','ed')] = value_elcct
      flows.loc['2020',(en_code+'_se','per','ed')] = value_elcct_loss
      
    ''' Including Biomass and Biomass CHP losses for 2020'''
    for en_code in ['enc']:
        biomass_powerplants_eff = 0.28 #JRC-2021 POWERGEN_EU27 file
        value_bm_loss = flows.loc['2020',(en_code + '_pe', 'elc_se','thm')].sum() * (1 / biomass_powerplants_eff - 1)
        flows.loc['2020',(en_code+'_pe','per','bm')] = value_bm_loss
        biomass_chp_elec_eff = 0.28
        value_bm_chp_elc = flows.loc['2020',(en_code + '_pe', 'elc_se','chp')].sum()
        value_bm_chp_heat = flows.loc['2020',(en_code + '_pe', 'vap_se','chp')].sum()
        input_bm_chp = value_bm_chp_elc / biomass_chp_elec_eff
        usefull_energy_bm_chp = value_bm_chp_elc + value_bm_chp_heat
        losses_bm_chp = input_bm_chp - usefull_energy_bm_chp
        flows.loc['2020',(en_code+'_pe','per','cc')] = losses_bm_chp
        
    ''' Including Oil fired powerplants and CHP losses for 2020'''
    for en_code in ['pet']:
        oil_powerplants_eff = 0.38 #JRC-2021 POWERGEN_EU27 file
        value_oil_loss = flows.loc['2020',(en_code + '_pe', 'elc_se','thm')].sum() * (1 / oil_powerplants_eff - 1)
        flows.loc['2020',(en_code+'_pe','per','lp')] = value_oil_loss
        oil_chp_elec_eff = 0.3
        value_oil_chp_elc = flows.loc['2020',(en_code + '_pe', 'elc_se','chp')].sum()
        value_oil_chp_heat = flows.loc['2020',(en_code + '_pe', 'vap_se','chp')].sum()
        input_oil_chp = value_oil_chp_elc / oil_chp_elec_eff
        usefull_energy_oil_chp = value_oil_chp_elc + value_oil_chp_heat
        losses_oil_chp = input_oil_chp - usefull_energy_oil_chp
        flows.loc['2020',(en_code+'_pe','per','cc')] = losses_oil_chp
        
    ''' Including Coal, Lignite fired powerplants and CHP losses for 2020'''
    for en_code in ['cms']:
        coal_powerplants_eff = 0.37 #JRC-2021 POWERGEN_EU27 file
        lignite_powerplants_eff = 0.33 #JRC-2021 POWERGEN_EU27 file
        value_coal_loss = flows.loc['2020',(en_code + '_pe', 'elc_se','thm')].sum() * (1 / coal_powerplants_eff - 1)
        value_lignite_loss = flows.loc['2020',(en_code + '_pe', 'elc_se','thmm')].sum() * (1 / lignite_powerplants_eff - 1)
        flows.loc['2020',(en_code+'_pe','per','lp')] = value_coal_loss
        flows.loc['2020',(en_code+'_pe','per','lg')] = value_lignite_loss
        coal_chp_elec_eff = 0.3
        value_coal_chp_elc = flows.loc['2020',(en_code + '_pe', 'elc_se','chp')].sum()
        value_coal_chp_heat = flows.loc['2020',(en_code + '_pe', 'vap_se','chp')].sum()
        input_coal_chp = value_coal_chp_elc / coal_chp_elec_eff
        usefull_energy_coal_chp = value_coal_chp_elc + value_coal_chp_heat
        losses_coal_chp = input_coal_chp - usefull_energy_coal_chp
        flows.loc['2020',(en_code+'_pe','per','cc')] = losses_coal_chp
        
    ''' Aggregating gas and hydrogen grid losses assuming 4% for gas grid and 5% for hydrogen network https://www.sciencedirect.com/science/article/pii/S0360544223005303'''
    for en_code in ['gaz']:
     value_gass_loss = flows[(en_code+'_se','gaz_fe','de')].squeeze().rename_axis(None) * 0.04
     flows[(en_code+'_se','per','de')] = value_gass_loss 
     #Including losses in total supply
     value_flow = flows[(en_code+'_pe','gaz_se','')].squeeze().rename_axis(None) 
     flows[(en_code+'_pe','gaz_se','')] = value_flow + value_gass_loss
    for en_code in ['pet']:
      value_pet_use = flows[(en_code+'_fe','ind','')].squeeze().rename_axis(None) * 0.5
      value_pet_loss = flows[(en_code+'_fe','ind','')].squeeze().rename_axis(None) * 0.5
      flows[('ind','use','pet')] = value_pet_use 
      flows[('ind','per','pet')] = value_pet_loss 
    for en_code in ['hyd']:
     value_hyd_loss = flows[(en_code+'_se','hyd_fe','')].squeeze().rename_axis(None) * 0.05
     flows[(en_code+'_se','per','fl')] = value_hyd_loss
    # Considering 15% losses from district heating network from pypsa
    for en_code in ['vap']:
     value_dh_loss = flows[(en_code+'_se','vap_fe','')].squeeze().rename_axis(None) * 0.15
     flows[(en_code+'_se','per','dl')] = value_dh_loss
     
    ''' Considering 3% distribution losses and 7% 400/230 V losses adopted from https://www.ofgem.gov.uk/sites/default/files/docs/2009/05/sohn-overview-of-losses-final-internet-version.pdf'''
    for en_code in ['res']:
     value_total_res = flows[('elc_fe','res','elc')].squeeze().rename_axis(None)
     value_total_ter = flows[('elc_fe','res','')].squeeze().rename_axis(None)
     value_total_elc = value_total_res + value_total_ter
     value_dist_loss = value_total_elc * 0.03
     value_sector_loss = value_total_elc * 0.07
     value_total_elec_use = value_total_elc * 0.9
     flows[(en_code,'per','dist')] = value_dist_loss
     flows[(en_code,'per','sect')] = value_sector_loss
     flows[(en_code,'use','')] = value_total_elec_use
     
    # Oil boiler losses
    oil_boiler_eff = options.loc[("decentral oil boiler", "efficiency"), "value"]
    for en_code in ['res']:
      value_oilb_a = flows[('pet_fe','res','oa')].squeeze().rename_axis(None) 
      value_oilb_b = flows[('pet_fe','res','ob')].squeeze().rename_axis(None)
      value_oilb_c = flows[('pet_fe','res','oc')].squeeze().rename_axis(None)
      value_oilb_d = flows[('pet_fe','res','od')].squeeze().rename_axis(None)
      val_oil_total = value_oilb_a + value_oilb_b + value_oilb_c + value_oilb_d
      value_oil_total_use = val_oil_total * oil_boiler_eff
      value_oil_total_loss = val_oil_total * (1 / oil_boiler_eff - 1)
      flows[(en_code,'per','oil')] = value_oil_total_loss
      
    # Oil boiler losses for 2020
    oil_boiler_eff_2020 = 0.65 #JRC-2021 Residential_EU27 file
    for en_code in ['res']:
      value_oilb_a_2020 = flows.loc['2020',('pet_fe','res','oa')].sum() 
      value_oilb_b_2020 = flows.loc['2020',('pet_fe','res','ob')].sum()
      value_oilb_c_2020 = flows.loc['2020',('pet_fe','res','oc')].sum()
      value_oilb_d_2020 = flows.loc['2020',('pet_fe','res','od')].sum()
      val_oil_total_2020 = value_oilb_a_2020 + value_oilb_b_2020 + value_oilb_c_2020 + value_oilb_d_2020
      value_oil_total_use_2020 = val_oil_total_2020 * oil_boiler_eff_2020
      value_oil_total_loss_2020 = val_oil_total_2020 * (1 / oil_boiler_eff_2020 - 1)
      flows.loc['2020',(en_code,'per','oil')] = value_oil_total_loss_2020
      
      
    # Gas boiler losses
    gas_boiler_eff = options.loc[("decentral gas boiler", "efficiency"), "value"]
    for en_code in ['res']:
      value_gasb_a = flows[('gaz_fe','res','ga')].squeeze().rename_axis(None) 
      value_gasb_b = flows[('gaz_fe','res','gb')].squeeze().rename_axis(None)
      value_gasb_c = flows[('gaz_fe','res','gc')].squeeze().rename_axis(None)
      value_gasb_d = flows[('gaz_fe','res','gd')].squeeze().rename_axis(None)
      value_gas_total = value_gasb_a+ value_gasb_b +value_gasb_c+value_gasb_d
      value_gas_total_use = value_gas_total * gas_boiler_eff
      value_gas_total_loss = value_gas_total * (1 / gas_boiler_eff - 1)
      flows[(en_code,'per','gas')] =value_gas_total_loss
      
    # Gas boiler losses for 2020
    gas_boiler_eff_2020 = 0.74 #JRC-2021 Residential_EU27 file
    for en_code in ['res']:
      value_gasb_a_2020 = flows.loc['2020',('gaz_fe','res','ga')].sum()
      value_gasb_b_2020 = flows.loc['2020',('gaz_fe','res','gb')].sum()
      value_gasb_c_2020 = flows.loc['2020',('gaz_fe','res','gc')].sum()
      value_gasb_d_2020 = flows.loc['2020',('gaz_fe','res','gd')].sum()
      value_gas_total_2020 = value_gasb_a_2020+ value_gasb_b_2020 +value_gasb_c_2020+value_gasb_d_2020
      value_gas_total_use_2020 = value_gas_total_2020 * gas_boiler_eff_2020
      value_gas_total_loss_2020 = value_gas_total_2020 * (1 / gas_boiler_eff_2020 - 1)
      flows.loc['2020',(en_code,'per','gas')] =value_gas_total_loss_2020

      
    # Biomass boiler losses
    biomass_boiler_eff = options.loc[("biomass boiler", "efficiency"), "value"]
    for en_code in ['res']:
      value_bm_a = flows[('enc_fe','res','ba')].squeeze().rename_axis(None) 
      value_bm_b = flows[('enc_fe','res','bb')].squeeze().rename_axis(None)
      value_bm_c = flows[('enc_fe','res','bc')].squeeze().rename_axis(None)
      value_bm_d = flows[('enc_fe','res','bd')].squeeze().rename_axis(None)
      value_bm_total = value_bm_a + value_bm_b + value_bm_c + value_bm_d
      value_bm_total_use = value_bm_total * biomass_boiler_eff
      value_bm_total_loss = value_bm_total * (1 / biomass_boiler_eff - 1)
      flows[(en_code,'per','bm')] = value_bm_total_loss
      #district heating
      value_dist = flows[('vap_fe','res','')].squeeze().rename_axis(None)
      
    # Biomass boiler losses for 2020
    biomass_boiler_eff_2020 = 0.7 #JRC-2021 Residential_EU27 file
    for en_code in ['res']:
      value_bm_a_2020 = flows.loc['2020',('enc_fe','res','ba')].sum() 
      value_bm_b_2020 = flows.loc['2020',('enc_fe','res','bb')].sum()
      value_bm_c_2020 = flows.loc['2020',('enc_fe','res','bc')].sum()
      value_bm_d_2020 = flows.loc['2020',('enc_fe','res','bd')].sum()
      value_bm_total_2020 = value_bm_a_2020 + value_bm_b_2020 + value_bm_c_2020 + value_bm_d_2020
      value_bm_total_use_2020 = value_bm_total_2020 * biomass_boiler_eff_2020
      value_bm_total_loss_2020 = value_bm_total_2020 * (1 / biomass_boiler_eff_2020 - 1)
      flows.loc['2020',(en_code,'per','bm')] = value_bm_total_loss_2020
      #district heating
      value_dist_2020= flows.loc['2020',('vap_fe','res','')].sum()
    
    # Resistive heaterlosses
    resistive_heater_eff = options.loc[("decentral resistive heater", "efficiency"), "value"]
    for en_code in ['res']:
      value_re_a = flows[('elc_fe','res','ea')].squeeze().rename_axis(None) 
      value_re_b = flows[('elc_fe','res','eb')].squeeze().rename_axis(None)
      value_re_c = flows[('elc_fe','res','ec')].squeeze().rename_axis(None)
      value_re_d = flows[('elc_fe','res','ed')].squeeze().rename_axis(None)
      value_re_e = flows[('elc_fe','res','ee')].squeeze().rename_axis(None) 
      value_re_f = flows[('elc_fe','res','ef')].squeeze().rename_axis(None)
      value_re_g = flows[('elc_fe','res','eg')].squeeze().rename_axis(None)
      value_re_h = flows[('elc_fe','res','eh')].squeeze().rename_axis(None)
      value_re_total = value_re_a+value_re_b+value_re_c+value_re_d+value_re_e+value_re_f+value_re_g+value_re_h
      value_re_total_use = value_re_total * resistive_heater_eff
      value_re_total_loss = value_re_total * (1 / resistive_heater_eff - 1)
      flows[(en_code,'per','ex')] = value_re_total_loss
      
    # Resistive heaterlosses for 2020
    resistive_heater_eff_2020 = 0.81 #JRC-2021 Residential_EU27 file
    for en_code in ['res']:
      value_re_a_2020 = flows.loc['2020',('elc_fe','res','ea')].sum()
      value_re_b_2020 = flows.loc['2020',('elc_fe','res','eb')].sum()
      value_re_c_2020 = flows.loc['2020',('elc_fe','res','ec')].sum()
      value_re_d_2020 = flows.loc['2020',('elc_fe','res','ed')].sum()
      value_re_e_2020 = flows.loc['2020',('elc_fe','res','ee')].sum() 
      value_re_f_2020 = flows.loc['2020',('elc_fe','res','ef')].sum()
      value_re_g_2020 = flows.loc['2020',('elc_fe','res','eg')].sum()
      value_re_h_2020 = flows.loc['2020',('elc_fe','res','eh')].sum()
      value_re_total_2020 = value_re_a_2020+value_re_b_2020+value_re_c_2020+value_re_d_2020+value_re_e_2020+value_re_f_2020+value_re_g_2020+value_re_h_2020
      value_re_total_use_2020 = value_re_total_2020 * resistive_heater_eff_2020
      value_re_total_loss_2020 = value_re_total_2020 * (1 / resistive_heater_eff_2020 - 1)
      flows.loc['2020',(en_code,'per','ex')] = value_re_total_loss_2020
      
      
    #heat pumps
    for en_code in ['res']:
      value_hp_a = flows[('elc_fe','res','ha')].squeeze().rename_axis(None) 
      value_hp_b = flows[('elc_fe','res','hb')].squeeze().rename_axis(None)
      value_hp_c = flows[('elc_fe','res','hc')].squeeze().rename_axis(None)
      value_hp_d = flows[('elc_fe','res','hd')].squeeze().rename_axis(None)
      value_hp_total = value_hp_a+value_hp_b+value_hp_c+value_hp_d
      value_ahp_a = flows[('pac_fe','res','aha')].squeeze().rename_axis(None) 
      value_ahp_b = flows[('pac_fe','res','ahb')].squeeze().rename_axis(None)
      value_ahp_c = flows[('pac_fe','res','ahc')].squeeze().rename_axis(None)
      value_ahp_d = flows[('pac_fe','res','ahd')].squeeze().rename_axis(None)
      value_ahp_total =value_ahp_a+value_ahp_b+value_ahp_c+value_ahp_d 
      value_ahp_total.loc[['2030', '2040','2050']] = [0, 0, 0]
      
    ''' Considering total heat losses in residential and tertiary heating with heat losses in buildings https://internationalcopper.org/wp-content/uploads/2022/04/Efficiency_First_PFLUGER_4.pdf'''
    value_total_heat = value_oil_total_use+value_gas_total_use+value_bm_total_use+value_dist+value_re_total_use+value_hp_total+value_ahp_total
    value_total_heat_2020 = value_oil_total_use_2020+value_gas_total_use_2020+value_bm_total_use_2020+value_dist_2020+value_re_total_use_2020+value_hp_total+value_ahp_total
    if scenario == "ref":
        total_buiding_losses = 0.4
        efficiency_imp_2020 = 0.1
        efficiency_imp_2030 = 0.1
        efficiency_imp_2040 = 0.2
        efficiency_imp_2050 = 0.3
        losses_2020 = total_buiding_losses * (1-efficiency_imp_2020)
        use_2020 = 1-losses_2020
        losses_2030 = total_buiding_losses * (1-efficiency_imp_2030)
        use_2030 = 1-losses_2030
        losses_2040 = total_buiding_losses * (1-efficiency_imp_2040)
        use_2040 = 1-losses_2040
        losses_2050 = total_buiding_losses * (1-efficiency_imp_2050)
        use_2050 = 1-losses_2050
        value_2020_use = value_total_heat_2020.loc['2020'] * use_2020
        value_2020_loss = value_total_heat_2020.loc['2020'] * losses_2020
        value_2030_use = value_total_heat.loc['2030'] * use_2030
        value_2030_loss = value_total_heat.loc['2030'] * losses_2030
        value_2040_use = value_total_heat.loc['2040'] * use_2040
        value_2040_loss = value_total_heat.loc['2040'] * losses_2040
        value_2050_use = value_total_heat.loc['2050'] * use_2050
        value_2050_loss = value_total_heat.loc['2050'] * losses_2050
        index = [2020, 2030, 2040, 2050]
        useful_total_buid = pd.Series(index=index, dtype=float)
        useful_total_buid.loc['2020'] = value_2020_use
        useful_total_buid.loc['2030'] = value_2030_use
        useful_total_buid.loc['2040'] = value_2040_use
        useful_total_buid.loc['2050'] = value_2050_use

        loss_total_buid = pd.Series(index=index, dtype=float)
        loss_total_buid.loc['2020'] = value_2020_loss
        loss_total_buid.loc['2030'] = value_2030_loss
        loss_total_buid.loc['2040'] = value_2040_loss
        loss_total_buid.loc['2050'] = value_2050_loss
        flows[('res','use','all')] = useful_total_buid
        flows[('res','per','all')] = loss_total_buid
        
    if scenario == "suff":
        total_buiding_losses = 0.4
        efficiency_imp_2020 = 0.1
        efficiency_imp_2030 = 0.3
        efficiency_imp_2040 = 0.5
        efficiency_imp_2050 = 0.8
        losses_2020 = total_buiding_losses * (1-efficiency_imp_2020)
        use_2020 = 1-losses_2020
        losses_2030 = total_buiding_losses * (1-efficiency_imp_2030)
        use_2030 = 1-losses_2030
        losses_2040 = total_buiding_losses * (1-efficiency_imp_2040)
        use_2040 = 1-losses_2040
        losses_2050 = total_buiding_losses * (1-efficiency_imp_2050)
        use_2050 = 1-losses_2050
        value_2020_use = value_total_heat_2020.loc['2020'] * use_2020
        value_2020_loss = value_total_heat_2020.loc['2020'] * losses_2020
        value_2030_use = value_total_heat.loc['2030'] * use_2030
        value_2030_loss = value_total_heat.loc['2030'] * losses_2030
        value_2040_use = value_total_heat.loc['2040'] * use_2040
        value_2040_loss = value_total_heat.loc['2040'] * losses_2040
        value_2050_use = value_total_heat.loc['2050'] * use_2050
        value_2050_loss = value_total_heat.loc['2050'] * losses_2050
        index = [2020, 2030, 2040, 2050]
        useful_total_buid = pd.Series(index=index, dtype=float)
        useful_total_buid.loc['2020'] = value_2020_use
        useful_total_buid.loc['2030'] = value_2030_use
        useful_total_buid.loc['2040'] = value_2040_use
        useful_total_buid.loc['2050'] = value_2050_use

        loss_total_buid = pd.Series(index=index, dtype=float)
        loss_total_buid.loc['2020'] = value_2020_loss
        loss_total_buid.loc['2030'] = value_2030_loss
        loss_total_buid.loc['2040'] = value_2040_loss
        loss_total_buid.loc['2050'] = value_2050_loss
        flows[('res','use','all')] = useful_total_buid
        flows[('res','per','all')] = loss_total_buid
      
    ''' Considering electricity efficiency of 90% for industrila manufacturing motors https://www.sciencedirect.com/science/article/pii/S1364032109002494?casa_token=yPrOEam4AEEAAAAA:udiAeMgscILNY2rDo__Zsmx81V4Un8j_Levpbr9WCet1Sdq-WaUZOzQ0S1d6z6LlugZOpaTKnCE#bib35'''
    for en_code in ['ind']:
       value_ind_elc = flows[('elc_fe','ind','ind')].squeeze().rename_axis(None)
       flows[(en_code,'use','ind')] = value_ind_elc * 0.9
       flows[(en_code,'per','ind')] = value_ind_elc * 0.1
       # considering 43% efficiency for coal proceses in industry
       value_ind_coal = flows[('cms_fe','ind','col')].squeeze().rename_axis(None)
       flows[(en_code,'use','col')] = value_ind_coal* 0.43
       flows[(en_code,'per','col')] = value_ind_coal * 0.57
       #hydrogen considering 100% efficiency
       value_ind_h2 = flows[('hyd_fe','ind','')].squeeze().rename_axis(None)
       flows[(en_code,'use','hh')] = value_ind_h2
       ''' Considering 1/3rd of industrial priocess heat by natural gas is lost https://betterbuildingssolutioncenter.energy.gov/sites/default/files/2024-04/2024Summit-Industrial_Process_Heat_Decarbonization-Slides.pdf'''
       value_ind_ng = flows[('gaz_fe','ind','ng')].squeeze().rename_axis(None)
       flows[(en_code,'use','ng')] = value_ind_ng* 0.65
       flows[(en_code,'per','ng')] = value_ind_ng * 0.35
       value_ind_ng_cc = flows[('gaz_fe','ind','ngcc')].squeeze().rename_axis(None)
       flows[(en_code,'use','ngcc')] = value_ind_ng_cc* 0.65
       flows[(en_code,'per','ngcc')] = value_ind_ng_cc * 0.35
       
       value_ind_bm = flows[('enc_fe','ind','sd')].squeeze().rename_axis(None)
       flows[(en_code,'use','sd')] = value_ind_bm* 0.65
       flows[(en_code,'per','sd')] = value_ind_bm * 0.35
       value_ind_bm_cc = flows[('enc_fe','ind','sdcc')].squeeze().rename_axis(None)
       flows[(en_code,'use','sdcc')] = value_ind_bm_cc* 0.65
       flows[(en_code,'per','sdcc')] = value_ind_bm_cc * 0.35
       value_ind_dh = flows[('vap_fe','ind','dhl')].squeeze().rename_axis(None)
       flows[(en_code,'use','dhl')] = value_ind_dh* 0.65
       flows[(en_code,'per','dhl')] = value_ind_dh * 0.35
    # for en_code in ['neind']:
    #    value_ind_ne = flows[('pet_fe','neind','non')].squeeze().rename_axis(None)
    #    value_ind_ne_hyd = flows[('hyd_fe','neind','non')].squeeze().rename_axis(None)
    #    flows[(en_code,'use','non')] = value_ind_ne
    #    flows[(en_code,'use','nom')] = value_ind_ne_hyd
       
    ''' Considering 40%,45% and 65% efficiency for maritime fleets based on oil, methanol and H2 https://sustainableworldports.org/wp-content/uploads/DNV-GL_2019_Maritime-forecast-to-2050-Energy-transition-Outlook-2019-report.pdf'''
    for en_code in ['wati']:
       value_mar_oil = flows[('pet_fe','wati','oil')].squeeze().rename_axis(None) 
       flows[(en_code,'use','oil')] = value_mar_oil * 0.4
       flows[(en_code,'per','oil')] = value_mar_oil * 0.6
       value_mar_met = flows[('met_fe','wati','met')].squeeze().rename_axis(None) 
       flows[(en_code,'use','met')] = value_mar_met * 0.45
       flows[(en_code,'per','met')] = value_mar_met * 0.55
       value_mar_h = flows[('hyd_fe','wati','hyd')].squeeze().rename_axis(None)
       flows[(en_code,'use','hyd')] = value_mar_h * 0.65
       flows[(en_code,'per','hyd')] = value_mar_h * 0.35
       
    ''' Considering 20%,91% and 65% efficiency for vehicle fleets based on ICE,EV and fuell cell https://witricity.com/media/blog/ev-vs-ice-surprising-differences'''
    for en_code in ['tra']:
       value_tra_oil = flows[('pet_fe','tra','oil')].squeeze().rename_axis(None) 
       flows[(en_code,'use','oil')] = value_tra_oil * 0.2
       flows[(en_code,'per','oil')] = value_tra_oil * 0.8
       value_ev_met = flows[('bev_fe','tra','ev')].squeeze().rename_axis(None) 
       flows[(en_code,'use','ev')] = value_ev_met * 0.91
       flows[(en_code,'per','ev')] = value_ev_met * 0.09
       value_tra_h = flows[('hyd_fe','tra','hyd')].squeeze().rename_axis(None)
       flows[(en_code,'use','hyd')] = value_tra_h * 0.65
       flows[(en_code,'per','hyd')] = value_tra_h * 0.35
    ''' Considering average 30% overall efficiency for aircrafts https://www.grida.no/climate/ipcc/aviation/097.htm'''
    for en_code in ['avi']:
       value_avi_oil = flows[('pet_fe','avi','')].squeeze().rename_axis(None) 
       flows[(en_code,'use','oil')] = value_avi_oil * 0.3
       flows[(en_code,'per','oil')] = value_avi_oil * 0.7 
    ''' Considering 88% electric motor efficiency and 35% for oil motors https://www.dpi.nsw.gov.au/__data/assets/pdf_file/0003/564780/electric-pumps-performance-and-efficiency.pdf'''
    for en_code in ['agr']:
       value_agri_oil = flows[('pet_fe','agr','')].squeeze().rename_axis(None) 
       value_agri_elc = flows[('elc_fe','agr','')].squeeze().rename_axis(None)
       value_agri_gas = flows[('gaz_fe','agr','')].squeeze().rename_axis(None)
       flows[(en_code,'use','oil')] = value_agri_oil * 0.35
       flows[(en_code,'per','oil')] = value_agri_oil * 0.65 
       flows[(en_code,'use','elc')] = value_agri_elc * 0.88
       flows[(en_code,'per','elc')] = value_agri_elc * 0.12
       flows[(en_code,'use','gas')] = value_agri_gas * 0.7
       flows[(en_code,'per','gas')] = value_agri_gas * 0.3
       
    ''' Considering 12.7% rail traction losses https://rail-research.europa.eu/wp-content/uploads/2024/07/ERSIPB-EDSIPB-B-S2R-219-01_-_20240314_Energy_saving_measures_in_rail_report_changes__2_.pdf'''
    for en_code in ['ras']:
       value_rail = flows[('elc_fe','ras','')].squeeze().rename_axis(None)
       value_rail_oil = flows[('pet_fe','ras','')].squeeze().rename_axis(None)
       flows[(en_code,'use','elc')] = value_rail * 0.873
       flows[(en_code,'per','elc')] = value_rail * 0.127 
       flows[(en_code,'use','oil')] = value_rail * 0.31
       flows[(en_code,'per','oil')] = value_rail * 0.69 
    
    '''Considering 5% efficiency of DAC https://pubs.acs.org/doi/10.1021/acsengineeringau.2c00043'''
    for en_code in ['dac']:
        value_elc_dac = flows[('elc_se','dac','')].squeeze().rename_axis(None)
        value_heat_dac = flows[('vap_se','dac','')].squeeze().rename_axis(None)
        flows[(en_code,'use','dec')] = value_elc_dac * 0.05
        flows[(en_code,'per','dec')] = value_elc_dac * 0.95 
        flows[(en_code,'use','dhc')] = value_heat_dac * 0.05
        flows[(en_code,'per','dhc')] = value_heat_dac * 0.95
        
    ## Storing energy flows, non-energy GHG values and other relevant values for each country
    tot_flows[country] = flows
    # tot_ghg[country] = flows_ghg
    # tot_co2[country] = flows_co2
    
    country_results = pd.DataFrame()
    tot_results = pd.concat([tot_results, country_results], axis=1)


def generate_results(flows, tot_results, country):
    xls_file_name = f"{scenario}/htmls/ChartData_{country}.xlsx"
    os.makedirs(os.path.dirname(xls_file_name), exist_ok=True)
    # xls_file_name = str(xls_file_name)
 
    file_handle = open(xls_file_name, 'wb')
    results_xls_writer = pd.ExcelWriter(file_handle, engine="openpyxl")

    if country in ALL_COUNTRIES:
        show_total = False
        country_list = COUNTRIES

    country_results = pd.DataFrame(columns=pd.MultiIndex(levels=[[],[]], codes=[[],[]], names=['Indicator','Sub_indicator']))
    global interval_time

    flows_bk =  flows.copy()
    
  
    # selected_columns = flows_bk.columns.get_level_values('Source').isin(FE_NODES)
    # # Sum the selected columns to calculate the FEC carrier
    # fec_carrier = flows_bk.loc[:, selected_columns]
    # grouped_fec = fec_carrier.groupby(level='Source', axis=1).sum()
    # fec_carrier = grouped_fec
    # selected_columns = flows_bk.columns.get_level_values('Target').isin(DS_NODES)

    # # Create a new DataFrame containing only the selected columns
    # fec_sector = flows_bk.loc[:, selected_columns]

    # # Group the columns by 'Target' (nodes) and sum each group separately
    # grouped_fec_sec = fec_sector.groupby(level='Target', axis=1).sum()
    # fec_sector = grouped_fec_sec

      
    # '''preparing data for local production area charts'''

    # selected_columns_E = flows_bk.columns.get_level_values('Target').isin(EE_NODES)
    # export_carrier = flows_bk.loc[:, selected_columns_E]
    # grouped_export = export_carrier.groupby(level='Source', axis=1).sum()
    # cov_exports = grouped_export
    # selected_columns_I = flows_bk.columns.get_level_values('Source').isin(II_NODES)
    # import_carrier = flows_bk.loc[:, selected_columns_I]
    # grouped_import = import_carrier.groupby(level='Target', axis=1).sum()
    # cov_imports = grouped_import
    
    # impexp_carriers = list(set(cov_imports.columns.to_list() + cov_exports.columns.to_list())) # Carriers with imports and/or exports only
    # # merged_carriers = pd.concat([grouped_export, grouped_import], axis=1).fillna(0)
    # target_flows_list = ['elc_se', 'cms_pe', 'met_fe', 'hyd_se', 'gaz_pe', 'amm_fe', 'enc_pe', 'vap_se', 'pet_pe']
    # ps_cons = pd.DataFrame()
    # for target_flow in target_flows_list:
    #  flows_sum = flows.xs(target_flow, level='Target', axis=1, drop_level=True).sum(axis=1)
    #  ps_cons[target_flow] = flows_sum
    # cov_ratios = 100 * ps_cons.subtract(cov_imports, fill_value=0).filter(impexp_carriers) / ps_cons.subtract(cov_exports, fill_value=0).filter(impexp_carriers)
    # value_gaz = flows_bk[('gaz_pe', 'gaz_se', '')].squeeze().rename_axis(None)
    # value_biogas = flows_bk[('bgl_pe', 'gaz_se', '')].squeeze().rename_axis(None)
    # value_biogas_cc = flows_bk[('bgl_pe', 'gaz_se', 'cc')].squeeze().rename_axis(None)
    # value_bl = flows_bk[('enc_pe', 'gaz_se', '')].squeeze().rename_axis(None)
    # value_hy = flows_bk[('hyd_se', 'gaz_se', '')].squeeze().rename_axis(None)
    # value_total = ((value_biogas + value_biogas_cc + value_bl + value_hy)/(value_gaz + value_biogas + value_biogas_cc + value_bl + value_hy))*100
    # cov_ratios['gaz_se'] = value_total
    # value_petr = flows_bk[('pet_pe', 'pet_fe', '')].squeeze().rename_axis(None)
    # value_biml = flows_bk[('enc_pe', 'pet_fe', '')].squeeze().rename_axis(None)
    # value_fish = flows_bk[('hyd_se', 'pet_fe', '')].squeeze().rename_axis(None)
    # value_toltal = ((value_biml + value_fish)/(value_petr + value_biml + value_fish))*100
    # cov_ratios['pet_fe'] = value_toltal
    # cov_ratios = cov_ratios.clip(upper=100)
    
    # '''preparing data for renewable share in each energy vector'''
    # ren_cov_ratios=pd.DataFrame()
    # gfec_breakdown=pd.DataFrame()
    # flows_from_node_cum=pd.DataFrame()
    # selected_columns_cr = flows_bk.columns.get_level_values('Source').isin(PE_NODES)
    # flows_from_node = flows_bk.loc[:, selected_columns_cr]
    # flows_from_node_cum = pd.concat([flows_from_node_cum,flows_from_node], axis=1).groupby(axis=1,level=[0,1,2]).sum()
    # flows_from_node = flows_from_node.groupby(level='Source', axis=1).sum()
    # selected_columns_de = flows_bk.columns.get_level_values('Source').isin(FE_NODES)
    # flows_to_node = flows_bk.loc[:, selected_columns_de]
    # flows_to_node = flows_to_node.groupby(level='Source', axis=1).sum()
    # ren_columns = ['spv_pe', 'eon_pe', 'eof_pe', 'hdr_pe', 'enc_pe', 'pac_pe','bgl_pe']
    # fos_columns = ['cms_pe', 'gaz_pe', 'pet_pe']
    # nuk_columns = ['ura_pe']

    # ren_sum = flows_from_node[ren_columns].sum(axis=1)
    # fos_sum = flows_from_node[fos_columns].sum(axis=1)
    # nuk_sum = flows_from_node[nuk_columns].sum(axis=1)

    # flows_from_node['ren'] = ren_sum.clip(lower=0)
    # flows_from_node['fos'] = fos_sum.clip(lower=0)
    # flows_from_node['nuk'] = nuk_sum.clip(lower=0)

    # flows_from_node_t = flows_from_node.drop(columns=ren_columns + fos_columns + nuk_columns)
    # gfec_breakdown = flows_from_node_t.loc[:, (flows_from_node_t != 0).any()]
    
    # tot_columns = ['spv_pe', 'eon_pe', 'eof_pe', 'hdr_pe', 'enc_pe', 'pac_pe','cms_pe', 'gaz_pe', 'pet_pe','ura_pe']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in tot_columns and col[1] == 'elc_se']
    # result_elc = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_elc_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_elc = ['spv_pe', 'eon_pe', 'eof_pe', 'hdr_pe', 'enc_pe']
    # ren_elc = result_elc[ren_elc].sum(axis=1)
    # ren_cov_ratios = pd.DataFrame()
    # ren_cov_ratios['elc_fe'] = (ren_elc/result_elc_t)*100
    # ren_cov_ratios['elc_fe'] = ren_cov_ratios['elc_fe']
    
    # gas_columns = ['bgl_pe','enc_pe', 'gaz_pe','hyd_se']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in gas_columns and col[1] == 'gaz_se']
    # result_gas = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_gas_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_gas = ['bgl_pe','enc_pe', 'hyd_se']
    # ren_gas = result_gas[ren_gas].sum(axis=1)
    # ren_cov_ratios['gaz_fe'] = (ren_gas/result_gas_t)*100
    # ren_cov_ratios['gaz_fe'] = ren_cov_ratios['gaz_fe']
    
    # pet_columns = ['pet_pe','enc_pe','hyd_se']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in pet_columns and col[1] in ['pet_fe', 'lqf_se']]
    # result_pet = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_pet_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_pet = ['enc_pe','hyd_se']
    # ren_pet = result_pet[ren_pet].sum(axis=1)
    # ren_cov_ratios['pet_fe'] = (ren_pet/result_pet_t)*100
    # ren_cov_ratios['pet_fe'] = ren_cov_ratios['pet_fe']
    
    # hyd_columns = ['elc_se','gaz_se','hyd_imp']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in hyd_columns and col[1] == 'hyd_se']
    # result_hyd = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_hyd_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_hyd = ['elc_se','hyd_imp']
    # ren_hyd = result_hyd[ren_hyd].sum(axis=1)
    # ren_cov_ratios['hyd_fe'] = (ren_hyd/result_hyd_t)*100
    # ren_cov_ratios['hyd_fe'] = ren_cov_ratios['hyd_fe']
    
    # bm_columns = ['enc_pe']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in bm_columns and col[1] in ['gaz_se', 'lqf_se', 'elc_se','vap_se','enc_fe']]
    # result_bm = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_bm_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_bm = ['enc_pe']
    # ren_bm = result_bm[ren_bm].sum(axis=1)
    # ren_cov_ratios['enc_fe'] = (ren_bm/result_bm_t)*100
    # ren_cov_ratios['enc_fe'] = ren_cov_ratios['enc_fe']
    
    # dh_columns = ['enc_pe','cms_pe','pet_pe','gaz_se','hyd_se','bgl_pe','elc_se','pac_pe','tes_se']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in dh_columns and col[1] in ['vap_se']]
    # result_dh = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_dh_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_dh = ['enc_pe','bgl_pe','elc_se','pac_pe', 'hyd_se', 'tes_se']
    # ren_dh = result_dh[ren_dh].sum(axis=1)
    # ren_cov_ratios['vap_fe'] = (ren_dh/result_dh_t)*100
    # ren_cov_ratios['vap_fe'] = ren_cov_ratios['vap_fe']
    
    # am_columns = ['pac_pe']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in am_columns and col[1] in ['vap_se','pac_fe']]
    # result_am = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_am_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_am = ['pac_pe']
    # ren_am = result_am[ren_am].sum(axis=1)
    # ren_cov_ratios['pac_fe'] = (ren_am/result_am_t)*100
    # ren_cov_ratios['pac_fe'] = ren_cov_ratios['pac_fe']
    
    # nh_columns = ['elc_se','hyd_se','amm_imp']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in nh_columns and col[1] in ['amm_fe']]
    # result_nh = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_nh_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_nh = ['elc_se','hyd_se','amm_imp']
    # ren_nh = result_nh[ren_nh].sum(axis=1)
    # ren_cov_ratios['amm_fe'] = (ren_nh/result_nh_t)*100
    # ren_cov_ratios['amm_fe'] = ren_cov_ratios['amm_fe']
    
    # me_columns = ['elc_se','hyd_se','met_imp']
    # filtered_columns = [col for col in flows_bk.columns if col[0] in me_columns and col[1] in ['met_fe']]
    # result_me = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum()
    # result_me_t = flows_bk[filtered_columns].groupby(level='Source', axis=1).sum().sum(axis=1)
    # ren_me = ['elc_se','hyd_se','met_imp']
    # ren_me = result_me[ren_me].sum(axis=1)
    # ren_cov_ratios['met_fe'] = (ren_me/result_me_t)*100
    # ren_cov_ratios['met_fe'] = ren_cov_ratios['met_fe']
    
    # gfec_breakdown_pct = sf.share_percent(gfec_breakdown,100)
    # ren_cov_ratios['total'] = gfec_breakdown_pct['ren']
    # ren_cov_ratios = ren_cov_ratios.clip(upper=100)
    
    # # interval_time = sf.calc_time('Graph analysis (consumption breakdown)', interval_time)

    # '''Preparing data foe emission charts'''
    # flows_co2 = tot_co2[country]
    # ghg_sector = tot_ghg[country]
    # ghg_sector = ghg_sector.groupby(level='Source', axis=1).sum()
    # ghg_sector['lufnes_ghg'] = -ghg_sector['lufnes_ghg']
    # ghg_sector['blg_ghg'] = -ghg_sector['blg_ghg']
    # ghg_sector['dac_ghg'] = -ghg_sector['dac_ghg']
    # ghg_sector['bec_ghg'] = -ghg_sector['bec_ghg']
    # ghg_sector['blq_ghg'] = -ghg_sector['blq_ghg']
    # ghg_sector['bmc_ghg'] = -ghg_sector['bmc_ghg']
    # ghg_source = tot_ghg[country].groupby(level='Target', axis=1).sum()
    # ghg_source['lufnes_ghg'] = -ghg_source['lufnes_ghg']
    # ghg_source['blg_ghg'] = -ghg_source['blg_ghg']
    # ghg_source['dac_ghg'] = -ghg_source['dac_ghg']
    # ghg_source['bec_ghg'] = -ghg_source['bec_ghg']
    # ghg_source['blq_ghg'] = -ghg_source['blq_ghg']
    # ghg_source['bmc_ghg'] = -ghg_source['bmc_ghg']
    
    # ghg_sector_cum = ghg_sector.copy()
    # ghg_sector_cum.loc['2030'] *= 10
    # ghg_sector_cum.loc['2040'] *= 10
    # ghg_sector_cum.loc['2050'] *= 10
    # #multiplying by 10 for cumulative emissions
    # ghg_source_cum = ghg_source.copy()
    # ghg_source_cum.loc['2030'] *= 10
    # ghg_source_cum.loc['2040'] *= 10
    # ghg_source_cum.loc['2050'] *= 10
    ## Start HTML output
    html_items = {}
    
    with open("plots.yaml", 'r') as file:
     plots = yaml.safe_load(file)
    sepia_plots = plots.get("Sepia_plots", {})
    print(sepia_plots)
    
    
    id_section = -1
    sections = [('ghg','CO2 emissions by sector'),('ghg','CO2 emissions by source'),('ghg','Cumulative CO2 emissions by sector'),('ghg','Cumulative CO2 emissions by source'),('sankey','Sankey diagram'),('carbon sankey','Carbon Sankey diagram'),('res','Renewable energy share'),('res','Final energy consumption by origin'),('carrier','Share of domestic production'),('cons','Final energy consumption by each sector'),('cons','Mix of secondary energies'),('cons','Final energy consumption by carrier for each sector')]
    sections = [(category, label) for category, label in sections if sepia_plots.get(label, False)]
    
    if MAIN_PARAMS['HTML_TEMPLATE'] == "raw": sections += [('input','Input data')]
    html_items['MENU'] = '<ol>'
    for (anchor,title) in sections:
        html_items['MENU'] += '<li><a href="#'+anchor+'">'+title+'</a></li>'
    html_items['MENU'] += '</ol>'

    html_items['MAIN'] = ''
    
    
    #load HTML Texts
    # file_path="/home/umair/pypsa-eur_repository/SEPIA"
    def load_html_texts(file_path):
     html_texts = {}
     with open(file_path, 'r') as file:
        for line in file:
            # Split by ": " to get the key and the HTML content
            if ": " in line:
                key, html_content = line.split(": ", 1)
                html_texts[key.strip()] = html_content.strip()
     return html_texts

    # Load the HTML texts from file
    html_texts = load_html_texts('html_texts.txt')
    country_specific_items = {}
    for key, text in html_texts.items():
        country_specific_items[f"{key}_{country}"] = text.format(country=country)
    # GHG
    if sepia_plots["CO2 emissions by sector"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += country_specific_items.get(f'CO2_emissions_sector_{country}', '') 
     # html_items['MAIN'] += saf.combine_charts([('',ghg_sector)], MAIN_PARAMS, NODES,'', 'ghgchart',  results_xls_writer, 'MtCO<sub>2</sub>eq') #('by sect. - power & heat dispatched',ghg_sector_2),
    if sepia_plots["CO2 emissions by source"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('CO2_emissions_source', '')
     # html_items['MAIN'] += saf.combine_charts([('',ghg_source)], MAIN_PARAMS, NODES,'', 'ghgchart', results_xls_writer, 'MtCO<sub>2</sub>eq')
    if sepia_plots["Cumulative CO2 emissions by sector"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('Cumulative_CO2_emissions_sector', '')
     # html_items['MAIN'] += saf.combine_charts([('',saf.cumul(ghg_sector_cum, 2020))], MAIN_PARAMS, NODES,'', 'ghgchart',  results_xls_writer, 'MtCO<sub>2</sub>eq')
    if sepia_plots["Cumulative CO2 emissions by source"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('Cumulative_CO2_emissions_source', '')
     # html_items['MAIN'] += saf.combine_charts([('',saf.cumul(ghg_source_cum,2020))], MAIN_PARAMS, NODES, '','ghgchart', results_xls_writer, 'MtCO<sub>2</sub>')

    # Sankeys
    if sepia_plots["Sankey diagram"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('sankey_diagram', '')
     html_items['MAIN'] += saf.combine_charts([('Sankey diagram',flows)], MAIN_PARAMS, NODES, '', 'sankey', sk_proc=PROCESSES) #('upstream flows from final energies',flows_from_node_cum),('Sankey diagram without import mix',flows)
    if sepia_plots["Carbon Sankey diagram"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('carbon_sankey_diagram', '')
     # html_items['MAIN'] += saf.combine_charts([('Carbon Sankey diagram',flows_co2)], MAIN_PARAMS, NODES, '', 'carbon sankey', sk_proc=PROCESSES_2) #('upstream flows from final energies',flows_from_node_cum),('Sankey diagram without import mix',flows)
    # RES share
    if sepia_plots["Renewable energy share"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('RES_share', '')
     # html_items['MAIN'] += sf.chart_to_output(sf.create_node_chart(ren_cov_ratios, NODES, MAIN_PARAMS, 'linechart', '', results_xls_writer, '%'))
    # html_items['MAIN'] += '<p>Renewable shares per final energies are calculated by analysing all energy flows going through different transformation processes (electricity and heat production processes, power-to-gas etc.) as described by the Sankey diagram. An algorithm goes upstream through this complex energy system, from a given final energy to all relevant primary energies, and determines their respective shares. For example, a renewable share of 50% for final electricity means that 50% of the electricity consumed has been produced by renewable means, either directly from renewable power technologies such as wind of PV, or indirectly - for example if gas cogeneration has been used with a share of renewables in the gas mix.'
    # if MAIN_PARAMS['USE_IMPORT_MIX'] and not show_total: html_items['MAIN'] += ' NB: the mix of imported secondary energy carriers (power, gas...) is calculated from exports of other EU countries, and may thus contain some level of renewables, included in this calculation as well.'
    if sepia_plots["Final energy consumption by origin"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('FEC_origin', '')
     if show_total: html_items['MAIN'] += sf.chart_to_output(sf.create_map(tot_results[('ren_cov_ratio','total')], country_list, 'RES share in final consumption', MAIN_PARAMS, unit='%', min_scale=0,max_scale=100))
     # html_items['MAIN'] += sf.chart_to_output(sf.create_node_chart(gfec_breakdown, NODES, MAIN_PARAMS, 'area', '', results_xls_writer))
    
    # Energy carrier share balance
    if sepia_plots["Share of domestic production"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('Domestic_production_share', '')
     # html_items['MAIN'] += sf.chart_to_output(sf.create_node_chart(cov_ratios, NODES, MAIN_PARAMS, 'linechart', 'Local production coverage ratios', results_xls_writer, unit='%'))
    # html_items['MAIN'] += '<p>Local production coverage ratios are simply defined as the ratio between the local production of a given energy carrier, and its local consumption (including final and non final uses). A ratio above 100% thus means that the country is more than self-sufficient (net exporter), while a ratio below 100% means that the country is a net importer.</p>'
     if show_total:
        node_list = tot_results['cov_ratio'].columns.unique(level='Sub_indicator').to_list()
        sf.put_item_in_front(node_list, 'total') # We put total first
        combinations = [(NODES.loc[node,'Label'],tot_results[('cov_ratio',node)]) for node in node_list]
        html_items['MAIN'] += saf.combine_charts(combinations, MAIN_PARAMS, country_list, 'Local prod coverage ratios -', 'map', results_xls_writer, '%', min_scale=0, mid_scale=50)
    
    # combinations = [('All energies',fec_sector)]
    # grouped_flows = flows.T.groupby(['Source', 'Target', 'Type']).sum().T
    # for energy in FE_NODES:
    #     combinations += [(NODES.loc[energy,'Label'], sf.node_consumption(grouped_flows, energy, direction='forward', splitby='target'))]
    if sepia_plots["Final energy consumption by each sector"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('FEC_sector', '')
     html_items['MAIN'] += saf.combine_charts(combinations, MAIN_PARAMS, NODES, 'Final consumption by sector -', 'areachart', results_xls_writer)
    # combinations = []
    # for energy in SE_NODES:
    #     df = sf.node_consumption(grouped_flows, energy, direction='backward', splitby='source')
    #     combinations += [(NODES.loc[energy,'Label'], df)]
    #     country_results = sf.add_indicator_to_results(country_results, df, 'sec_mix.'+energy, False)
    if sepia_plots["Mix of secondary energies"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     html_items['MAIN'] += html_texts.get('Grid_carrier_contribution', '')
     html_items['MAIN'] += saf.combine_charts(combinations, MAIN_PARAMS, NODES, 'Mix of secondary energies -', 'areachart', results_xls_writer)
    # html_items['MAIN'] += '<p>The above chart describes the contribution of misc. technologies (and possibly imports) to the production of a given secondary energy carrier.</p>'
    combinations = []
    # Energy consumption
    if sepia_plots["Final energy consumption by carrier for each sector"] == True:
     id_section += 1
     html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
     combinations = [('All sectors',fec_carrier)]
     # for sector in DS_NODES:
     #    df = sf.node_consumption(grouped_flows, sector, direction='backwards', splitby='target')
     #    combinations += [(NODES.loc[sector,'Label'], df)]
     #    country_results = sf.add_indicator_to_results(country_results, df, 'fec.'+sector)
     html_items['MAIN'] += html_texts.get('FEC_carrier', '')
     html_items['MAIN'] += saf.combine_charts(combinations, MAIN_PARAMS, NODES, 'Final consumption by carrier -', 'areachart', results_xls_writer)
    

    # Indicator calculation for inter-territorial analysis
    # Multidimensionnal indicators not already defined above (some indicators have several nomenclatures: by energy / sector / origin etc.)
    # for (indicator,df) in [('fec',fec_carrier),('fec',fec_sector),('cov_ratio',cov_ratios),('ren_cov_ratio',ren_cov_ratios),('ghg_sector',ghg_sector),('ghg_source',ghg_source)]:
        # country_results = sf.add_indicator_to_results(country_results, df, indicator)
    
    # for indicator in ['fec','ghg_sector']:
        # country_results[(indicator,'reduc')] = sf.reduction_rate(country_results[(indicator,'total')],100)
    
    ## List of input files
    if MAIN_PARAMS['HTML_TEMPLATE'] == "raw":
        id_section += 1
        html_items['MAIN'] += sf.title_to_output(sections[id_section][1], sections[id_section][0], MAIN_PARAMS['HTML_TEMPLATE'])
        # html_items['MAIN'] += '<p>Input data taken from: <b>'+input_file_label+'</b></p>'
    current_time = datetime.datetime.now().strftime("%d/%m/%Y %Hh%M")
    html_items['MAIN'] += f'<p style="text-align:right;font-size:small;">SEPIA v{__version__} @ {current_time}</p>'
    
    ## Writing HTML file
    # for country in ALL_COUNTRIES:
    template = "Template/pypsa_previous.html"
    with open(template) as f:
        html_output = f.read()
    for label in html_items:
        html_output = html_output.replace('{{'+label+'}}', html_items[label])
    filename = f"{scenario}/htmls/Results_{country}.html"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    # filename = str(filename)
    with open(filename, 'w') as f:
        f.write(html_output)
    
    
    # Table of content for ChartData
    toc = results_xls_writer.book.create_sheet('TOC')
    for (i,sheet) in enumerate(results_xls_writer.sheets):
        if sheet != "TOC":
            toc['A'+str(i+1)].value = sheet
            toc['B'+str(i+1)].hyperlink = "#'"+sheet+"'!A1"
            toc['B'+str(i+1)].value = results_xls_writer.sheets[sheet]['A1'].value
            toc['B'+str(i+1)].style = 'Hyperlink'
            back_to_toc = results_xls_writer.sheets[sheet]['A2']
            back_to_toc.hyperlink = "#TOC!A1"
            back_to_toc.value = 'Back to table of contents'
            back_to_toc.style = 'Hyperlink'
            disclaimer = 'Results shown below are not to be disseminated to third parties' if MAIN_PARAMS['DRAFT'] else 'This work is licensed under a Creative Commons Attribution 4.0 International License.'
            disclaimer += f' SEPIA v{__version__} @ {current_time}'
            results_xls_writer.sheets[sheet]['D2'] = disclaimer
    results_xls_writer.book.active = toc
    results_xls_writer.close()
    return tot_results


for country in ALL_COUNTRIES:
    tot_results = generate_results(tot_flows[country], tot_results, country)
    
