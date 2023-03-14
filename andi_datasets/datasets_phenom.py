# AUTOGENERATED! DO NOT EDIT! File to edit: ../source_nbs/lib_nbs/datasets_phenom.ipynb.

# %% auto 0
__all__ = ['datasets_phenom']

# %% ../source_nbs/lib_nbs/datasets_phenom.ipynb 2
from .models_phenom import models_phenom

import inspect
import numpy as np
import pandas as pd
import csv
from tqdm.auto import tqdm
import copy

import os
import warnings

# %% ../source_nbs/lib_nbs/datasets_phenom.ipynb 5
class datasets_phenom():
    def __init__(self,
                models_class = models_phenom()):
            ''' 
            This class generates, saves and loads datasets of trajectories simulated from various phenomenological diffusion models (available at andi_datasets.models_phenom). 
            '''
            self.models_class = models_class
            self._get_models()
        
    def _get_models(self):        
        '''Loads the available models from the subclass'''

        available_models = inspect.getmembers(self.models_class, inspect.ismethod)      
        available_models = available_models[1:][::-1] # we need this to get rid of the init
        self.avail_models_name = [x[0] for x in available_models]
        self.avail_models_func = [x[1] for x in available_models]
        
    def _get_inputs_models(self, model, get_default_values = False):
        ''' Given the name of a phenom model, returns the inputs to that model '''
        
        model_f = self.avail_models_func[self.avail_models_name.index(model)] 
        defaults = inspect.getfullargspec(model_f).defaults
        params = inspect.getfullargspec(model_f).args[1:]
        if get_default_values:
            return params, defaults
        else:
            return params

# %% ../source_nbs/lib_nbs/datasets_phenom.ipynb 7
class datasets_phenom(datasets_phenom):
                
    def create_dataset(self,
                       dics: list|dict|bool = False,
                       T: None|int = None,
                       N_model: None|int = None,  
                       path: str = '',
                       save: bool = False,
                       load: bool = False):
        ''' 
        Given a list of dictionaries, generates trajectories of the demanded properties.
        The only compulsory input for every dictionary is `model`, i.e. the model from which 
        trajectories must be generated. The rest of inputs are optional.
        You can see the input parameters of the different models in `andi_datasets.models_phenom`,
        This function checks and handles the input dataset and the manages both the creation,
        loading and saving of trajectories.
        
        Parameters
        ----------
        dics : list, dictionary, bool
            - if list or dictionary: the function generates trajectories with the properties stated in each dictionary.
            - if bool: the function generates trajectories with default parameters set for the ANDI 2 challenge (phenom) for every available diffusion model.
        T : int, None
            - if int: overrides the values of trajectory length in the dictionaries.
            - if None: uses the trajectory length values in the dictionaries. 
            Caution: the minim T of all dictionaries will be considered!
        N_model : int, None
            - if int: overrides the values of number of trajectories in the dictionaries.
            - if None: uses the number of trajectories in the dictionaries
        save : bool
            If True, saves the generated dataset (see self._save_trajectories).
        load : bool
            If True, loads a dataset from path (see self._load_trajectories).
        path : str
            Path from where to save or load the dataset.
            
        Returns
        -------
        tuple
            - trajs (array TxNx2): particles' position. N considers here the sum of all trajectories generated from the input dictionaries. 
            - labels (array TxNx2): particles' labels (see ._multi_state for details on labels) 
        '''
        
        self.T = T
        self.N_model = N_model
        self.path = path
        self.dics = dics
        
        'Managing dictionaries'
        # If the input is a single dictionary, transform it to list
        if isinstance(self.dics, dict): self.dics = [self.dics]
        # if dics is False, we select trajectories from all models with default values
        if self.dics is False: self.dics = [{'model': model} for model in self.avail_models_name]

                    
        'Managing folders of the datasets'
        self.save = save
        self.load = load
        if self.save or self.load:                
            if self.load:
                self.save = False            
            if not os.path.exists(self.path) and self.load:
                raise FileNotFoundError('The directory from where you want to load the dataset does not exist')                
            if not os.path.exists(self.path) and self.save:
                os.makedirs(self.path) 
                
                
        'Create trajectories'
        trajs, labels = self._create_trajectories()
        
        return trajs, labels                        

# %% ../source_nbs/lib_nbs/datasets_phenom.ipynb 12
class datasets_phenom(datasets_phenom):   
    
    def _create_trajectories(self): 
        ''' 
        Given a list of dictionaries, generates trajectories of the demanded properties.
        First checks in the .csv of each demanded model if a dataset of similar properties exists. 
        If it does, it loads it from the corresponding file.       
        
        Returns
        ----------
        tuple
            data_t  array containing the generated trajectories
            data_l  array containing the corresponding labels.
        '''

        for dic in copy.deepcopy(self.dics):
            
            df, dataset_idx = self._inspect_dic(dic)
            
            # If the dataset does not yet exists
            if dataset_idx is False:
                # Retrieve name and function of diffusion model
                model_f = self.avail_models_func[self.avail_models_name.index(dic['model'])]
                # Create dictionary with only arguments
                dic_args = dict(dic); dic_args.pop('model')
                
                trajs, labels = model_f(**dic_args)
                
                # Save the trajectories if asked
                if self.save:
                    self._save_trajectories(trajs = trajs,
                                            labels = labels,
                                            dic = dic, 
                                            df = df,
                                            dataset_idx = dataset_idx,
                                            path = self.path)                    
            else:
                trajs, labels = self._load_trajectories(model_name = dic['model'],
                                                        dataset_idx = dataset_idx,
                                                        path = self.path)
                
            # Stack dataset
            try:
                data_t = np.hstack((data_t, trajs))                    
                data_l = np.hstack((data_l, labels))
            except:
                data_t = trajs
                data_l = labels
                    
        return data_t, data_l  
    
    def _save_trajectories(self, trajs, labels, dic, df, dataset_idx, path):
        ''' 
        Given a set of trajectories and labels, saves two things:        
            - In the .csv corresponding to the demanded model, all the input parameters of the generated dataset. This allows to keed that of what was created before.
            - In a .npy file, the trajectories and labels generated.
        '''
        
        file_name = path+dic['model']+'_'+str(df.shape[0])+'.npy'
        
        # Save information in CSV handler
        df = df.append(dic, ignore_index = True) 
        #print(dic)
        #df = pd.concat([df, 
        #                pd.DataFrame(dic)], 
        #               ignore_index=True)        
        df.to_csv(path+dic['model']+'.csv')
        
        # Save trajectories and labels
        data = np.dstack((trajs, labels))
        np.save(file_name, data)
        
    def _load_trajectories(self, model_name, dataset_idx, path):
        ''' 
        Given the path for a dataset, loads the trajectories and labels
        '''
        
        file_name = path+model_name+'_'+str(dataset_idx)+'.npy'
        data = np.load(file_name)
        return data[:, :, :2], data[:, :  , 2:]
    

# %% ../source_nbs/lib_nbs/datasets_phenom.ipynb 21
class datasets_phenom(datasets_phenom):   

    def _inspect_dic(self, dic):
        '''        
        Checks the information of the input dictionaries so that they fulfil the constraints of the program , completes missing information
        with default values and then decides about loading/saving depending on parameters.
        
        Parameters
        ----------
        dic : dict
            Dictionary with the information of the trajectories we want to generate
        
        Returns
        -----------
        tuple
            df: dataframe collecting the information of the dataset to load.
            dataset_idx: location in the previous dataframe of the particular dataset we want to generate.
            
        '''        
            
        # Add time and number of trajectories information
        if self.N_model is not None:
            dic['N'] = self.N_model
        if self.T is not None:
            dic['T'] = self.T

        # Check if CSV with information of dataset exists. If not, create it
        model_m = dic['model']
        model_f = self.avail_models_func[self.avail_models_name.index(model_m)]    
        # Check arguments and defaults from model's function            
        args = inspect.getfullargspec(model_f).args[1:]
        defaults = inspect.getfullargspec(model_f).defaults
        try:
            df = pd.read_csv(self.path+model_m+'.csv', index_col=0)
        except:                
            # convert to dataframe and add model
            df = pd.DataFrame(columns = args+['model'])   
        # Assign missing keys in dic with default values
        for arg, default in zip(args, defaults):
            if arg not in dic.keys():
                dic[arg] = default

        # Check if updated keys of dic equal keys of csv.
        if set(list(df.keys())) != set(list(dic.keys())):
            raise ValueError('Input model dictionary does not match models properties')

        # Check if the dataset already exists:
        df_conditions = df.copy()
        # Nones in dataframes are transformed into Nans. We change back this here
        # but instead of putting None, we put False.
        df_conditions = df_conditions.where(pd.notnull(df_conditions), False)
        for key in dic:
            # Transforming Nones to False in variables dictionaries (see problem with df just above) 
            if dic[key] is None: dic[key] = False
            # We need to transform it to str to do a fair comparison between matrices (e.g. transition matrix, Ds, alphas,...)
            df_conditions = df_conditions.loc[(df_conditions[key].astype(str) == str(dic[key]))]
            if len(df_conditions.index) == 0:                
                break
        
        
        # If dataset exists
        if len(df_conditions.index) > 0:
            # if the dataset exists and save was True, do not save but load
            if self.save:
                wrn_str = f'The dataset you want to save already exists (file: {model_m}_{df_conditions.index[0]}.npy). Switching to Load mode.'
                warnings.warn(wrn_str)
                dataset_idx = df_conditions.index[0] 
            elif self.load:
                dataset_idx = df_conditions.index[0]
            else:
                dataset_idx = False                 

        # If dataset does no exists
        else:         
            if self.load:
                raise ValueError('The dataset you want to load does not exist.')
            else: # If the dataset does not exist, append empty string.
                # This allows to mix saving and loading
                dataset_idx = False
                
        return df, dataset_idx

# %% ../source_nbs/lib_nbs/datasets_phenom.ipynb 34
class datasets_phenom(datasets_phenom):  
    def _get_args(self, model, return_defaults = False):
        ''' 
        Given the name of a diffusion model, return its inputs arguments.
        
        Parameters
        ----------
        model : str
            Name of the diffusion model (see self.available_models_name)
        return_defaults : bool
            If True, the function will also return the default values of each input argument.
            
        Returns
        -------
        tuple
            args (list): list of input arguments.
            defaults (optional, list): list of default value for the input arguments.
        '''
        model_f = self.avail_models_func[self.avail_models_name.index(model)]    
        # Check arguments and defaults from model's function            
        args = inspect.getfullargspec(model_f).args[1:]
        defaults = inspect.getfullargspec(model_f).defaults
        if return_defaults:
            return args, defaults
        else:
            return args
