import numpy as np
import pandas as pd
import re


def norm_empresa(value : str) -> str:
    """
    Normaliza en nombre de la empresa a buscar
    """
    nombre = str(value)
    nombre_up = nombre.upper()
    nombre_split = nombre_up.split("-")
    nombre_split_low = nombre_split[0].strip()
    return nombre_split_low

def norm_factura(value : str) -> str:
    """
    Normaliza las facturas
    """
    factura = str(value)
    if factura == '': return ''

    try:
        sec, fac = factura.split("-")
        ret = f"{int(sec)}-{int(fac)}"
    except ValueError:
        ret = ''
    return ret


def normalizations(exp_value : str):
    """
    Elimina los espacios y normaliza la forma del expediente a:
    EX-YYYY-NNNNNNNNN- -APN-AAAAAA#AAAAA
    """
    unnormal_value = exp_value
    unnormal_value =  unnormal_value.strip()
    unnormal_value_no_space = unnormal_value.replace(" ", "").strip()
    
    index_d_hi, offset = ((unnormal_value_no_space.find("--"), 0) if unnormal_value_no_space.find("--")>=0 else
                          (unnormal_value_no_space.find("-APN"),1))
    lower_exp = unnormal_value_no_space[:index_d_hi]
    lower_exp = lower_exp.replace("EX", "EX-") if lower_exp.find("EX-")<0 else lower_exp
    number = lower_exp[8:]
    try:
        lower_exp = f"{lower_exp[:8]}{int(number)}"
    except ValueError:
        pass
    higher_exp = unnormal_value_no_space[index_d_hi+2-offset:]

    normalized_exp = f"{lower_exp}- -{higher_exp}"

    return normalized_exp


def id_tram_space_norm(exp : str) -> str:
    ident = exp
    
    string_exp = ''
    
    
    if isinstance(ident, float) and np.isnan(ident):
        return ''
    else:
        string_exp = str(ident).rstrip().strip()
    
    if string_exp.find('#') >= 0 and string_exp.find('EX') >= 0:
        unnormal = string_exp
        normalized = normalizations(unnormal)
        match = re.search('(\\d{5,})', normalized)
        if match is not None:
            num = match.group(1)
            normalized = normalized.replace(num, str(num))
        return normalized
    
    elif string_exp.find('#') >= 0 and string_exp.find('EX-') <0 and string_exp.find('X-')>=0:
        unnormal = f"E{string_exp}"
        normalized = normalizations(unnormal)
        match = re.search('(\\d{5,})', normalized)
        if match is not None:
            num = match.group(1)
            normalized = normalized.replace(num, str(num))
        return normalized

    return string_exp


def check_benef(row : object, nombre_p : str, nombre_s : str) -> str:
    contenido_p = str(row[nombre_p])
    contenido_s = str(row[nombre_s]).lower()
    low_ = contenido_p.lower()
    index = contenido_s.find(low_)
    msg = "No"
    if index >=0 : msg = "Si"
    return msg

def mask_creator(DF : pd.DataFrame, DF2 : pd.DataFrame,
                     DF_cols : list, DF2_cols : list) -> pd.Series:
        mask = (
        DF.set_index(DF_cols).index
           .isin(DF2.set_index(DF2_cols).index)
        )
        return mask

def group_dupl(df : pd.DataFrame, columns : str = "Ejercicio-Número") -> pd.DataFrame:

    df = df.fillna('').infer_objects(copy=False)
    df[columns] = df[columns].astype("string")
    cols = df.columns.drop(columns).to_list()
    if isinstance(columns, list):
        func_args = {}
        for i in columns:
            func_args[i] = lambda x: "/".join(x)
        ret_df = df.groupby(by = cols, as_index=False).agg(func_args)
    else:
        ret_df = df.groupby(by = cols, as_index=False).agg({columns : lambda x: "/".join(x)})
    return ret_df

def join_values(datos : np.array):
    
    string = ""
    for element in datos:
        string = f"{string}{element}/"
    string = string[:-1]
    
    return string


def second_lookup(DF_TO_LOOK : pd.DataFrame, DF_TO_LOOK_FOR : pd.DataFrame,
                  looking : str, lookout : str, column_of_DF_2 : str, date : bool = False,
                  date_column = "Fecha de Pago", date_data_column = "Año-Mes-Día",
                  regexpress = '(\\d{5,})'):
    
    DF_TO_LOOK[lookout] = DF_TO_LOOK[lookout].astype("string")
    mask = (DF_TO_LOOK[lookout].isna()) | (DF_TO_LOOK[lookout]=="")
    
    #print(mask)
    for idx in DF_TO_LOOK.index[mask]:
        text = DF_TO_LOOK.at[idx, looking]
        if len(text)>6:
            get_me = DF_TO_LOOK_FOR[column_of_DF_2].str.contains(text, regex=False)
            get_me = get_me.astype("boolean").fillna(False).infer_objects(copy=False)
            if get_me.sum()==0:
                mat = re.search(regexpress, text)
                if not mat is None:
                    finder = mat.group()
                    get_me = DF_TO_LOOK_FOR[column_of_DF_2].str.contains(finder, regex=False)
                    get_me = get_me.astype("boolean").fillna(False).infer_objects(copy=False)
            if len(DF_TO_LOOK_FOR[get_me])>0:
                DF_TO_USE = DF_TO_LOOK_FOR[get_me].copy()
                DF_TO_USE = group_dupl(DF_TO_USE)
                DF_TO_LOOK.at[idx, lookout] = join_values(DF_TO_USE["Ejercicio-Número"].values)
                if date:
                    DF_TO_LOOK.at[idx, date_column] = join_values(DF_TO_USE[date_data_column].values)
                    

    return DF_TO_LOOK


