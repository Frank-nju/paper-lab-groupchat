import os, yaml

def load_config(path):
    with open(path,'r',encoding='utf-8') as f: c=yaml.safe_load(f)
    if 'models' not in c or 'rebattle' not in c: raise ValueError('config needs models and rebattle')
    return c
