#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 24 12:45:44 2025

@author: umair
"""

import SEPIA_additional_functions as saf # Custom functions
import SEPIA_functions as sf # Custom functions
import pandas as pd # Read/analyse data
import datetime # For current time
import logging
import numpy as np
import yaml
import os

def biomass_potentials():
    # Create an empty DataFrame
    ALL_COUNTRIES = ['BE', 'DE', 'FR', 'GB', 'NL']
    planning_horizons = [2020,2030,2040,2050]
    cluster = '6'
    cluster = cluster[0]
    df = pd.DataFrame(index=planning_horizons, columns=ALL_COUNTRIES)

    # Iterate over countries and planning horizons
    for country in ALL_COUNTRIES:
        for planning_horizon in planning_horizons:
         if planning_horizon != 2020:
            biomass_potentials_file = f"/home/umair/pypsa-eur-master/resources/ref/biomass_potentials_s_{cluster}_{planning_horizon}.csv"
            biomass_p = pd.read_csv(biomass_potentials_file, index_col=0)
            
            # Convert MWh to TWh
            biomass_p = biomass_p / 1E6
            biomass_p.index = biomass_p.index.str[:2]
            biomass_p = biomass_p.groupby(biomass_p.index).sum()
            if planning_horizon == 2020:
                biomass_p[:] = 0
            # Assign the summed biomass potential for the country and planning horizon to the DataFrame
            df.loc[planning_horizon, country] = biomass_p.loc[country, 'solid biomass']

    return df

def prepare_sepia(countries):
 '''This function prepares data from excel files for sepia visulaisation'''

 # Import country data
 file = "/home/umair/pypsa-eur-master/SEPIA/COUNTRIES.xlsx"
 COUNTRIES = pd.read_excel(file, index_col=0)
 ALL_COUNTRIES = ['BE', 'DE', 'FR', 'GB', 'NL']
 fn = "/home/umair/pypsa-eur-master/data/costs_2050.csv"
 options = pd.read_csv(fn ,index_col=[0, 1]).sort_index()

 # Import config data (nodes, processes, general settings etc.)
 file = "/home/umair/pypsa-eur-master/SEPIA/SEPIA_config.xlsx"
 CONFIG = pd.read_excel(file, ["MAIN_PARAMS","NODES","PROCESSES","PROCESSES_2","PROCESSES_3","IMPORT_MIX","INDICATORS","GAS_PRO","OIL_PRO"], index_col=0)

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

 # # Energy system (network graph) creation for all countries
 # print("\nEnergy system (network graph) creation\n")
 # print("ALL_COUNTRIES:", ALL_COUNTRIES)
 # print("snakemake.input.excelfile:", snakemake.input.excelfile)
 
 for country in ALL_COUNTRIES:
    datafile = f"/home/umair/pypsa-eur-master/results/ref/sepia/inputs{country}.xlsx"
    # datafile = str(datafile)
    
    '''load energy input data for Sepia'''
    data = pd.read_excel(datafile, sheet_name="Inputs", index_col=0, usecols="C:G")
    data.reset_index(drop=True, inplace=False)
    data=data.T
    
    
    '''load co2 input data for Sepia'''
    data_co2 = pd.read_excel(datafile, sheet_name="Inputs_co2", index_col=0, usecols="C:G")
    data_co2.reset_index(drop=True, inplace=False)
    data_co2=data_co2.T
    
    '''Remove any duplicated data'''
    data = data.loc[:,~data.columns.duplicated()] 
    data_co2 = data_co2.loc[:,~data_co2.columns.duplicated()]# Remove duplicate indicators

    '''Consider the coding used in sepia config and put unfound demands from pypsa file to zero'''
    unfound_inputs = []
    unfound_inputs.extend(sf.unfound_indicators(data,PROCESSES,'Value_Code'))
    unfound_inputs.extend(sf.unfound_indicators(data,PROCESSES,'Efficiency_Code'))
    unfound_inputs.extend(sf.unfound_indicators(data,INDICATORS,'Value_Code'))
    if len(unfound_inputs)>0:
        data = data.reindex(columns=[*data.columns.tolist(), *unfound_inputs], fill_value=0)
        print("! Warning: the following indicators have not been found (they have been filled with 0): "+", ".join(unfound_inputs)+" !!!")
        
    unfound_inputs_co2 = []
    unfound_inputs_co2.extend(sf.unfound_indicators(data_co2,PROCESSES_2,'Value_Code'))
    if len(unfound_inputs_co2)>0:
        data_co2 = data_co2.reindex(columns=[*data_co2.columns.tolist(), *unfound_inputs_co2], fill_value=0)
        print("! Warning: the following indicators have not been found (they have been filled with 0): "+", ".join(unfound_inputs_co2)+" !!!")

    # ## Corrections on input data
    # Renaming indicators, based on INDICATORS sheet
    data = data.rename(columns=dict(zip(INDICATORS['Value_Code'],INDICATORS.index)))
    data = data.loc[:,~data.columns.duplicated()] # Remove duplicate indicators
    data_co2 = data_co2.rename(columns=dict(zip(INDICATORS['Value_Code'],INDICATORS.index)))
    data_co2 = data_co2.loc[:,~data_co2.columns.duplicated()]
    data_ghg = data_co2.copy()
    

    ## Creating flows filling values which do not require calculation, directly from input data
    proc_without_calc = PROCESSES[PROCESSES['Value_Code'].isin(data.columns)] # indicator is not empty and found in data
    flows = pd.DataFrame(data[proc_without_calc.Value_Code].values, index=data.index, columns=pd.MultiIndex.from_tuples(list(zip(proc_without_calc.Source, proc_without_calc.Target, proc_without_calc.Type)), names=('Source','Target','Type')))
    proc_without_calc_co2 = PROCESSES_2[PROCESSES_2['Value_Code'].isin(data_co2.columns)] # indicator is not empty and found in data
    flows_co2 = pd.DataFrame(data_co2[proc_without_calc_co2.Value_Code].values, index=data_co2.index, columns=pd.MultiIndex.from_tuples(list(zip(proc_without_calc_co2.Source, proc_without_calc_co2.Target, proc_without_calc_co2.Type)), names=('Source','Target','Type')))
    proc_without_calc_ghg = PROCESSES_3[PROCESSES_3['Value_Code'].isin(data_ghg.columns)] # indicator is not empty and found in data
    flows_ghg = pd.DataFrame(data_ghg[proc_without_calc_ghg.Value_Code].values, index=data_ghg.index, columns=pd.MultiIndex.from_tuples(list(zip(proc_without_calc_ghg.Source, proc_without_calc_ghg.Target, proc_without_calc_ghg.Type)), names=('Source','Target','Type')))


    '''Attaching production from primary and secondary energies to final energy demands'''
    selected_columns = flows.columns.get_level_values('Source').isin(FE_NODES)
    fec_carrier = flows.loc[:, selected_columns]
    grouped_fec = fec_carrier.groupby(level='Source', axis=1).sum()
    fec = grouped_fec
    for en_code in ['vap','elc','gaz','hyd','bev']:
        flows[(en_code+'_se',en_code+'_fe','')] = fec[en_code+'_fe']
    
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
    
    ''' Adding missing values for nuclear losses'''
    nuc_eff = options.loc[("nuclear", "efficiency"), "value"]
    nuc_los = (1 - nuc_eff)/nuc_eff
    for en_code in ['ura']:
      value_loss_nuc_2020 = flows.loc['2020', (en_code + '_pe', 'elc_se', 'thm')].sum() * nuc_los
      value_loss_nuc_2030 = flows.loc['2030', (en_code + '_pe', 'elc_se', 'thm')].sum() * nuc_los
      value_loss_nuc_2040 = flows.loc['2040', (en_code + '_pe', 'elc_se', 'thm')].sum() * nuc_los
      value_loss_nuc_2050 = flows.loc['2050', (en_code + '_pe', 'elc_se', 'thm')].sum() * nuc_los
      flows.loc['2020', (en_code + '_pe', 'per', 'thm')] = value_loss_nuc_2020
      flows.loc['2030', (en_code + '_pe', 'per', 'thm')] = value_loss_nuc_2030
      flows.loc['2040', (en_code + '_pe', 'per', 'thm')] = value_loss_nuc_2040
      flows.loc['2050', (en_code + '_pe', 'per', 'thm')] = value_loss_nuc_2050
    
    '''Attaching local production and imports'''
    selected_columns_p = flows.columns.get_level_values('Source').isin(PE_NODES)
    fec_carrier_p = flows.loc[:, selected_columns_p]
    grouped_fec_p = fec_carrier_p.groupby(level='Source', axis=1).sum()
    fec_p = grouped_fec_p
    countries = ['BE', 'DE', 'FR', 'GB', 'NL']
    if country == 'EU':
     for en_code in ['hdr','eon','eof','spv','pac','enc','bgl','win']:
        flows[('prod',en_code+'_pe','')] = fec_p[en_code+'_pe']
    else: 
     for en_code in ['hdr','eon','eof','spv','pac','bgl','win']:
        flows[('prod',en_code+'_pe','')] = fec_p[en_code+'_pe'] 
    for en_code in ['cms','ura']:
       flows[('imp',en_code+'_pe','')] = fec_p[en_code+'_pe'] 
    for en_code in ['gaz']:
     if country != 'EU':
      values = fec_p[en_code + '_pe']
      local_val = LOCAL_GAS.loc[country]
      local_val.index = local_val.index.map(str)
      mask = values >= local_val
      flows[('prod', en_code+'_pe', '')] = np.where(mask, local_val, values)
      flows[('imp', en_code+'_pe','')] =  np.where(mask, values - local_val, 0)
     else:
      values = fec_p[en_code + '_pe']
      local_val = LOCAL_GAS.loc[LOCAL_GAS.index.intersection(countries)].sum()
      local_val.index = local_val.index.map(str)
      mask = values >= local_val
      flows[('prod', en_code+'_pe', '')] = np.where(mask, local_val, values)
      flows[('imp', en_code+'_pe','')] =  np.where(mask, values - local_val, 0)
    for en_code in ['pet']:
     if country != 'EU':
      values = fec_p[en_code + '_pe']
      local_val = LOCAL_OIL.loc[country]
      local_val.index = local_val.index.map(str)
      mask = values >= local_val
      flows[('prod', en_code+'_pe', '')] = np.where(mask, local_val, values)
      flows[('imp', en_code+'_pe', '')] = np.where(mask, values - local_val, 0)
     else:
      values = fec_p[en_code + '_pe']
      local_val = LOCAL_OIL.loc[LOCAL_OIL.index.intersection(countries)].sum()
      local_val.index = local_val.index.map(str)
      mask = values >= local_val
      flows[('prod', en_code+'_pe', '')] = np.where(mask, local_val, values)
      flows[('imp', en_code+'_pe', '')] = np.where(mask, values - local_val, 0)
    
    value_bm_data = flows[('prod', 'enc_pe', '')].squeeze().rename_axis(None)
    ''' Compute biomass imports and local production from model data'''
    df = biomass_potentials()
    if country != 'EU':
     df[country] = df[country].astype(float)
     bm_potentials = df[[country]]
     bm_potentials = bm_potentials.loc[:, country].values
     for en_code in ['enc']:
      flows[('prod',en_code+'_pe','')] = bm_potentials
      flows.loc['2020', ('prod', en_code + '_pe', '')] = value_bm_data['2020']
      imp_values = fec_p[en_code + '_pe'] - bm_potentials
      imp_values2020 = fec_p[en_code + '_pe']['2020'] - value_bm_data['2020']
      flows[('imp', en_code + '_pe', '')] = imp_values
      flows.loc['2020', ('imp', en_code + '_pe', '')] = imp_values2020
      flows[(en_code + '_pe', 'exp', '')] = bm_potentials - fec_p[en_code + '_pe']
    
    sec_imports = flows.columns.get_level_values('Target').isin(SE_NODES)
    sec_imports = flows.loc[:, sec_imports]
    sec_imports = sec_imports.groupby(level='Target', axis=1).sum()
    if country != 'EU':
     for en_code in ['elc','hyd']:
        values_exp = sec_imports[en_code + '_se'] - fec_se[en_code + '_se']
        values_imp = fec_se[en_code + '_se'] - sec_imports[en_code + '_se']
        values_imp = values_imp.clip(lower=0)
        values_exp = values_exp.clip(lower=0)
        flows[('imp',en_code + '_se', '')] = values_imp
        flows[(en_code+'_se','exp','')] = values_exp
        
    other_imports = flows.columns.get_level_values('Target').isin(FE_NODES)
    other_imports = flows.loc[:, other_imports]
    other_imports = other_imports.groupby(level='Target', axis=1).sum() 
    if country != 'EU':
     for en_code in ['amm','met']:
        values_elec = flows[('elc_se',en_code + '_fe', '')].squeeze().rename_axis(None)
        flows[('met_fe','per', '')] = values_elec
        values_exp = other_imports[en_code + '_fe'] - fec_pe[en_code + '_fe'] - values_elec
        values_imp = fec_pe[en_code + '_fe'] - other_imports[en_code + '_fe'] - values_elec
        values_imp = values_imp.clip(lower=0)
        values_exp = values_exp.clip(lower=0)
        flows[('imp',en_code + '_fe', '')] = values_imp
        flows[(en_code+'_fe','exp','')] = values_exp
    else:
        values_elec = flows[('elc_se','met_fe', '')].squeeze().rename_axis(None)
        flows[('met_fe','per', '')] = values_elec
    '''preparing co2 emissions for carbon sankey'''
    tot_emm_s = flows_co2.columns.get_level_values('Source').isin(GHG_SECTORS)
    tot_emm_s = flows_co2.loc[:, tot_emm_s]
    tot_emm_s = tot_emm_s.groupby(level='Source', axis=1).sum() 
    
    # '''using co2 intensities from pypsa and compuing it from demands as on pypsa they are solved on EU level'''
    co2_intensity_gas = options.loc[("gas", "CO2 intensity"), "value"]
    co2_intensity_oil = options.loc[("oil", "CO2 intensity"), "value"]
    co2_intensity_met = options.loc[("methanolisation", "carbondioxide-input"), "value"]
    # demand_side_emm = flows.columns.get_level_values('Target').isin(DS_NODES)
    # demand_side_emm = flows.loc[:, demand_side_emm]
    # demand_side_emm = demand_side_emm.groupby(level='Target', axis=1).sum() 
    # for en_code in ['fol']:
    #     values_oil_emm = fec_p['pet_pe']
    #     flows_co2[(en_code + '_ghg', 'oil_ghg', '')] = values_oil_emm * co2_intensity_oil
    if country != 'EU':     
     for en_code in ['fgs']:
        # values_agr_emm = flows[('gaz_fe','agr', '')].squeeze().rename_axis(None) * co2_intensity_gas
        values_gas_emm = fec_p['gaz_pe'] 
        # flows_co2[(en_code + '_ghg', 'gas_ghg', '')] = values_gas_emm * co2_intensity_gas
        flows_co2.loc['2030', (en_code + '_ghg', 'gas_ghg', '')] = values_gas_emm['2030'] * co2_intensity_gas
        flows_co2.loc['2040', (en_code + '_ghg', 'gas_ghg', '')] = values_gas_emm['2040'] * co2_intensity_gas
        flows_co2.loc['2050', (en_code + '_ghg', 'gas_ghg', '')] = values_gas_emm['2050'] * co2_intensity_gas
    # for en_code in ['oil']:
    #     value_so = flows[('pet_fe', 'wati', '')].squeeze().rename_axis(None) * co2_intensity_oil
    #     value_naph = flows[('pet_fe', 'neind', '')].squeeze().rename_axis(None)
    #     value_ker = flows[('pet_fe', 'avi', '')].squeeze().rename_axis(None)
    #     value_tra = flows[('pet_fe', 'tra', '')].squeeze().rename_axis(None) * co2_intensity_oil
    #     value_tot =  value_naph * co2_intensity_oil
    #     flows_co2[(en_code + '_ghg', 'atm', 'so')] = value_so
    #     flows_co2[(en_code + '_ghg', 'atm', 'oil')] = value_tot
    #     flows_co2[(en_code + '_ghg', 'atm', 'tra')] = value_tra
  
    
    for en_code in ['oil']: 
      val_naphtha = flows[('pet_fe', 'neind', '')].squeeze().rename_axis(None)
      val_nonen = flows_co2[('pro_ghg', 'atm', '')].squeeze().rename_axis(None).sum(axis=1)
      flows_co2.loc['2020', ('oil_ghg', 'atm', 'oil')] = (val_naphtha['2020'] * co2_intensity_oil) - val_nonen['2020']
    tot_emm = flows_co2.columns.get_level_values('Target').isin(GHG_SECTORS)
    tot_emm = flows_co2.loc[:, tot_emm]
    tot_emm = tot_emm.groupby(level='Target', axis=1).sum() 
    for en_code in ['net']:
        # bm_cap = flows_co2[('atm', 'bec' + '_ghg', '')].squeeze().rename_axis(None)
        blg_cap = flows_co2[('atm', 'blg' + '_ghg', '')].squeeze().rename_axis(None)
        blg_cap_cc = flows_co2[('atm', 'blg' + '_ghg', 'cc')].squeeze().rename_axis(None)
        dac_cap = flows_co2[('atm', 'stm', '')].squeeze().rename_axis(None)
        # bm_cap = bm_cap.sum(axis=1)
        values_atm = tot_emm['atm'] - tot_emm['bm_ghg'] - tot_emm['luf_ghg'] - dac_cap - blg_cap - blg_cap_cc
        flows_co2[('atm',en_code + '_ghg',  'net')] = values_atm
        
    if country != 'EU':
     for en_code in ['met']:
      met_dem = fec_pe[en_code + '_fe']
      met_pro = flows[('hyd_se',en_code + '_fe', '')].squeeze().rename_axis(None)
      imp_met = (met_dem - met_pro) * co2_intensity_met 
      flows_co2[('hth_ghg',en_code + '_ghg', '')] = imp_met
      exp_met = (met_pro - met_dem) * co2_intensity_met
      flows_co2[(en_code + '_ghg',  'eth_ghg', '')] = exp_met
    # for en_code in ['pet']:
    #     flows_ghg[('ind_ghg',  en_code + '_pe', 'oil')] = value_tot
    #     flows_ghg[('tra_ghg',  en_code + '_pe', '')] = value_tra
       
    # for en_code in ['wati']:
    #     flows_ghg[(en_code + '_ghg', 'pet_pe',  '')] =value_so
    
    # for en_code in ['pet']:
    #     if flows[('hyd_se',en_code + '_fe',  '')].squeeze().rename_axis(None).sum()>0:
    #         pet_pro = flows[('hyd_se', en_code + '_fe', '')].squeeze().rename_axis(None)
    #         pet_bm = flows[('enc_pe', en_code + '_fe', '')].squeeze().rename_axis(None)
    #         value_agr = flows[('pet_fe', 'agr', '')].squeeze().rename_axis(None) 
    #         tot_pet = pet_pro + pet_bm 
    #         exp_pet = tot_pet - value_ker - value_naph -  value_agr
    #         flows[(en_code + '_fe', 'exp', '')] = exp_pet
    if country != 'EU':
     for en_code in ['gaz']:
        if (
    (flows[('hyd_se', en_code + '_se',  '')].squeeze().rename_axis(None).sum() > 0) or
    (flows[('bgl_pe', en_code + '_se',  'cc')].squeeze().rename_axis(None).sum() > 0)):
            tot_pro = biogas_p + biosng_p + meth_p + biogas_cc
            gas_dem = flows[(en_code + '_se', en_code + '_fe','')].squeeze().rename_axis(None)
            gas_los = flows[(en_code + '_se', 'per','')].squeeze().rename_axis(None)
            if isinstance(gas_los, pd.DataFrame):
              gas_los = gas_los.sum(axis=1)
            gas_elc = flows[(en_code + '_se', 'elc_se', '')].squeeze().rename_axis(None)
            if isinstance(gas_elc, pd.DataFrame):
              gas_elc = gas_elc.sum(axis=1)
            gas_vap = flows[(en_code + '_se', 'vap_se', '')].squeeze().rename_axis(None)
            if isinstance(gas_vap, pd.DataFrame):
              gas_vap = gas_vap.sum(axis=1)
            gas_smr = flows[(en_code + '_se', 'hyd_se', 'smr')].squeeze().rename_axis(None)
            if isinstance(gas_smr, pd.DataFrame):
              gas_smr = gas_smr.sum(axis=1)
            tot_dem = gas_dem + gas_los + gas_elc + gas_vap + gas_smr
            exp_gas = tot_pro - tot_dem
            flows[(en_code + '_se', 'exp', '')] = exp_gas
    for en_code in ['exg']:
        exp_emm = flows[('gaz' + '_se', 'exp', '')].squeeze().rename_axis(None) * co2_intensity_gas
        flows_co2[('gas_ghg',en_code + '_ghg', '')] = exp_emm
    # for en_code in ['ext']:
    #     exp_emm_p = flows[('pet' + '_fe', 'exp', '')].squeeze().rename_axis(None) * co2_intensity_oil
    #     flows_co2[('oil_ghg',en_code + '_ghg', '')] = exp_emm_p
    tot_em = flows_co2.columns.get_level_values('Source').isin(GHG_SECTORS)
    tot_em = flows_co2.loc[:, tot_em]
    tot_em = tot_em.groupby(level='Source', axis=1).sum() 
    for en_code in ['oil']: 
      value_pet_emm = tot_em[en_code+'_ghg']['2020']
      flows_co2.loc['2020', ('fol_ghg', en_code + '_ghg', '')] = value_pet_emm
      
    gas_df = flows_co2.columns.get_level_values('Source').isin(['gas_ghg'])
    gas_df = flows_co2.loc[:, gas_df]
    gas_df = gas_df.groupby(level='Target', axis=1).sum()
    gas_df = gas_df['atm']
    for en_code in ['fgs']: 
      value_gas_emm = gas_df['2020']
      flows_co2.loc['2020', ('fgs_ghg','gas_ghg', '')] = value_gas_emm
    for en_code in ['ind']: 
      value_ind = flows_co2[('oil_ghg', 'atm', 'oil')].squeeze().rename_axis(None)
      flows_ghg.loc['2020', ('ind_ghg','pet_pe', 'oil')] = value_ind['2020']
    
    filtered_flows = [
    ('imp', 'gaz_pe', ''),
    ('imp', 'pet_pe', ''),
    ('imp', 'elc_se', ''),
    ('imp', 'hyd_se', ''),
    ('imp', 'enc_pe', ''),
    ('imp', 'amm_fe', ''),
    ('imp', 'met_fe', ''),
    ('ura_pe', 'elc_se', 'thm'),
    ('imp', 'cms_pe', '')]
    selected_imports = pd.DataFrame()
    for flow in filtered_flows:
     if flow in flows.columns:
        selected_imports["_".join([flow[0], flow[1]]).replace(" ", "_")] = flows[flow]
    local_production = [
    ('prod', 'gaz_pe', ''),
    ('prod', 'pet_pe', ''),
    ('prod', 'hdr_pe', ''),
    ('prod', 'eon_pe', ''),
    ('prod', 'eof_pe', ''),
    ('prod', 'enc_pe', ''),
    ('prod', 'spv_pe', ''),
    ('prod', 'pac_pe', ''),
    ('prod', 'cms_pe', ''),
    ('prod', 'bgl_pe', ''),
    ('prod', 'win_pe', ''),]
    local_prod = pd.DataFrame()
    for flow in local_production:
     if flow in flows.columns:
        local_prod["_".join([flow[0], flow[1]]).replace(" ", "_")] = flows[flow]
    exports = [
    ('elc_se', 'exp', ''),
    ('hyd_se', 'exp', ''),
    ('enc_pe', 'exp', ''),
    ('met_fe', 'exp', ''),
    ('amm_fe', 'exp', ''),
    ('gaz_se', 'exp', ''),]
    
    exports_prod = pd.DataFrame()
    for flow in exports:
     if flow in flows.columns:
        exports_prod["_".join([flow[0], flow[1]]).replace(" ", "_")] = flows[flow]
    # output_dir = f"results/{study}/country_csvs"
    # os.makedirs(output_dir, exist_ok=True)
    # selected_imports.to_csv(f"{output_dir}/total_imports_{country}.csv", index=True)
    # local_prod.to_csv(f"{output_dir}/local_product_{country}.csv", index=True) 
    # exports_prod.to_csv(f"{output_dir}/exports_{country}.csv", index=True) 
    ## Storing energy flows, non-energy GHG values and other relevant values for each country
    tot_flows[country] = flows
    tot_ghg[country] = flows_ghg
    tot_co2[country] = flows_co2
    
    country_results = pd.DataFrame()
    tot_results = pd.concat([tot_results, country_results], axis=1)
ALL_COUNTRIES = ['BE', 'DE', 'FR', 'GB', 'NL']

for country in ALL_COUNTRIES:   
 prepare_sepia(country)