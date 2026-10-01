# -*- coding: utf-8 -*-


import numpy as np
import pandas as pd
import re
import time
from zipfile import ZipFile
from modulo_de_funciones import (id_tram_space_norm, group_dupl, join_values, second_lookup,
                                 deteccion_de_expedientes)




def execute(DF_SB_PROV : pd.DataFrame, DF_SAF : pd.DataFrame,
            expediente : str = "EXPEDIENTE PAGADOR", suffix : str ="(auto)",
            forget : bool = False) -> pd.DataFrame:


    """
    Función para la búsqueda y agregado de número y ejercicio de SG, PRE, PG y Fecha de Pago
    de forma automática utilizando un archivo xlsx obtenido de un agente automático de OBIEE.
    
    Args:
        DF_SB_PROV : DataFrame conteniendo el los valores a buscar con la columna 'expediente'.
        DF_SAF : DataFrame donde se ejecuta la búsqueda.
        expediente : Nombre de la columna donde se ejecuta la búsqueda
        suffix : Sufijo para identificar las columnas generadas.
        forget : En caso de ser verdadero, se eliminan las columnas SG{suffix}, PG{suffix},
                 f"PRE{suffix}", SG {suffix}, PG {suffix}, PRE {suffix}, Año-Mes-Día, Fecha de Pago
                 del DataFrame de entrada (DF_SB_PROV).

    Returns:
        DataFrame con las columnas agregadas, en caso que no existan, SG{suffix}, PRE{suffix}, PG{suffix}
        y Fecha de Pago, junto con una columna de EXPEDIENTE__SIN__NORMALIZAR.

    
    """
    
    if forget:
        #Se eliminan las columnas definidas (de existir) en <columns_to_forget> 
        columns_to_forget = [f"SG{suffix}", f"PG{suffix}", f"PRE{suffix}", f"SG {suffix}", f"PG {suffix}",
                         f"PRE {suffix}", "Año-Mes-Día", "Fecha de Pago"]

        for column_item in columns_to_forget:
            if column_item in DF_SB_PROV.columns.to_list(): DF_SB_PROV.drop(column_item, axis=1, inplace=True)
    
    #Se Eliminan los valores nulos para la columna 'Id. Tramite Normalizado'
    DF_SAF.dropna(subset=["Id. Tramite Normalizado"], inplace = True)
    DF_SAF["Ejercicio-Número"] = DF_SAF["Ejercicio-Número"].astype("string") 

    #Normalización de los valores en 'Id. Tramite Normalizado'; espacios, cantidad de -, etc.
    DF_SAF["Id. Tramite Normalizado"] = DF_SAF["Id. Tramite Normalizado"].apply(id_tram_space_norm)
    DF_SB_PROV["EXPEDIENTE__SIN__NORMALIZAR"] = DF_SB_PROV[expediente]
    DF_SB_PROV[expediente] = DF_SB_PROV[expediente].apply(id_tram_space_norm)
    

    #Se conservan solamente las columnas necesarias para la búsqueda, el resto de columnas que se obtienen del reporte se olvidan.
    DF_PRE = DF_SAF[DF_SAF["Tipo"] == "PRE"][["Identificador", "Id. Tramite Normalizado", "Ejercicio-Número",
                                              "Observaciones", "Identificación"]].copy().drop_duplicates(subset="Ejercicio-Número")
    
    DF_PG = DF_SAF[DF_SAF["Tipo"] == "PG"][["Cpte. Origen Único", "Identificador", "Id. Tramite Normalizado", "Ejercicio-Número",
                                            "Año-Mes-Día", "$IMCL Vigente", "Observaciones", "Identificación",
                                            "Observaciones Cpte origen"]].copy().drop_duplicates(subset="Ejercicio-Número")
    
    DF_SG = DF_SAF[DF_SAF["Tipo"] == "SG"][["Identificador", "Id. Tramite Normalizado", "Ejercicio-Número",
                                            "Observaciones", "Identificación"]].copy().drop_duplicates(subset="Ejercicio-Número") 

    DF_PG["Cpte. Origen Único"] = DF_PG["Cpte. Origen Único"].apply(lambda x : x.strip().rstrip())
    #Para el caso de los comprobantes PG, se tienen en cuenta los que tengan montos 'vigentes' mayores a 0, indicando que no tienen CMR
    DF_PG = DF_PG[DF_PG["$IMCL Vigente"]>0.].copy()
    #Se descarta la columna de monto vigente para el caso de los PG, ya que no se utilizará en adelante
    DF_PG.drop("$IMCL Vigente", axis=1, inplace=True)
    

    cols = ["Id. Tramite Normalizado", "Identificador"]

    
    #En caso que las columnas de llenado automático no existan, se crean vacías  
    columns_DF_SB_PROV = DF_SB_PROV.columns.to_list()
    if not f"SG{suffix}" in columns_DF_SB_PROV:
        DF_SB_PROV[f"SG{suffix}"] = DF_SB_PROV.apply(lambda _ : np.nan, axis=1).astype("string")
    if not f"PRE{suffix}" in columns_DF_SB_PROV:
        DF_SB_PROV[f"PRE{suffix}"] = DF_SB_PROV.apply(lambda _ : np.nan, axis=1).astype("string")
    if not f"PG{suffix}" in columns_DF_SB_PROV:
        DF_SB_PROV[f"PG{suffix}"] = DF_SB_PROV.apply(lambda _ : np.nan, axis=1).astype("string")
    if not "Fecha de Pago" in columns_DF_SB_PROV:
        DF_SB_PROV["Fecha de Pago"] = DF_SB_PROV.apply(lambda _ : np.nan, axis=1).astype("string")
    else:
        DF_SB_PROV["Fecha de Pago"] = DF_SB_PROV["Fecha de Pago"].astype("string")
        
    
   
    MERGE = DF_SB_PROV.copy()

    #Ejecución del código de búsqueda mediante la función 'second_lookup', ver módulo 'mod_func.py'
    #Búsca en las observaciones

    #full_regexpress = "EX-\\d{4}-\\d{1,}-?\\s*-\\s*APN-[A-Za-z]{1,}#[A-Za-z]{1,}(?=[ -]|[\\r\\n]|$)"
    full_regexpress = '(\\d{5,})'
    MERGE = second_lookup(MERGE, DF_SG, expediente, f"SG{suffix}", "Observaciones", regexpress = full_regexpress)
    MERGE = second_lookup(MERGE, DF_PRE, expediente, f"PRE{suffix}", "Observaciones", regexpress = full_regexpress)
    MERGE = second_lookup(MERGE, DF_PG, expediente, f"PG{suffix}", "Observaciones", True, regexpress = full_regexpress)
    MERGE = second_lookup(MERGE, DF_PG, expediente, f"PG{suffix}", "Observaciones Cpte origen", True, regexpress = full_regexpress)
    
    #Búsca en la columna 'Id. Tramite Normalizado' del reporte obtenido del BI
    
    MERGE = second_lookup(MERGE, DF_SG, expediente, f"SG{suffix}", "Id. Tramite Normalizado", regexpress = full_regexpress)
    MERGE = second_lookup(MERGE, DF_PRE, expediente, f"PRE{suffix}", "Id. Tramite Normalizado", regexpress = full_regexpress)
    MERGE = second_lookup(MERGE, DF_PG, expediente, f"PG{suffix}", "Id. Tramite Normalizado", True, regexpress = full_regexpress)
    

    return MERGE

def ejecucion_del_codigo(nombre_archivo_salida : str, data_frame : pd.DataFrame or [pd.DataFrame],
                            hojas : str or [str], data_frame_comparacion : pd.DataFrame, 
                            columna_expediente : str or [str], index_out : bool = False,
                            columnas_a_retornar = ["EXPEDIENTE__SIN__NORMALIZAR", "SG(auto)",
                            "PRE(auto)", "PG(auto)", "Fecha de Pago"]) -> None:
                            
    print(f"Inicio de la creación del archivo: {nombre_archivo_salida}")     
    with pd.ExcelWriter(nombre_archivo_salida) as writer:
        conc = None
        for data, nombre, columna in zip(data_frame, hojas, columna_expediente):
            res = execute(data, data_frame_comparacion)
            res.to_excel(writer, sheet_name=nombre, index=index_out)
        print(50*"-")
        print(f"Finalizó la creación de las hojas: {hojas}")
        print(50*"-")


if __name__ == '__main__':
    from pathlib import Path
    import warnings

    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
    
    directorio_script = Path(__file__).resolve().parent

   
    directorio_SB = f"{directorio_script}\\BASES SERVICIOS BASICOS\\"
    directorio_PROV = f"{directorio_script}\\BASES PROVEEDORES\\"

    #********************************************************************************
    #ÚNICA LÍNEA A MODIFICAR, DE SER NECESARIO:
    ARCHIVO = "OneDrive_2026-10-01.zip"
    archivos = [ARCHIVO, f"{ARCHIVO.replace('.zip',' (1).zip')}"]
    #CAMBIAR EL NOMBRE DEL ARCHIVO DESCARGADO DESDE OneDrive
    #********************************************************************************
    
    for archivo_comprimido in archivos:
        try:
            with ZipFile(f"{directorio_script}\\{archivo_comprimido}", 'r') as zipped:
                zipped.extractall()
        except FileNotFoundError as error:
            print(f"No se encontró el archivo: {archivo_comprimido}")
            exit(-1)


    hojas_SAF = ["SAF 311", "SAF 330", "SAF 350", "SAF 388"]
    DF_SAFS = pd.read_excel(f"{directorio_script}\\Reporte_PG_PRE_SG_311_341.xlsx", skiprows=4, sheet_name=hojas_SAF)
    DF_SAF_311 = DF_SAFS["SAF 311"]
    DF_SAF_330 = DF_SAFS["SAF 330"]
    DF_SAF_350 = DF_SAFS["SAF 350"]
    DF_SAF_388 = DF_SAFS["SAF 388"]


    DF_SB_311 = pd.read_excel(f"{directorio_SB}311 - SERVICIOS BASICOS - NIÑEZ.xlsx")    
    DF_SB_330 = pd.read_excel(f"{directorio_SB}330 - SERVICIOS BASICOS - EDUCACION.xlsx", sheet_name = "330")
    hojas_350 = ["CENTRAL", "AT"]
    DF_SB_350 =  pd.read_excel(f"{directorio_SB}350 - SERVICIOS BASICOS - TRABAJO.xlsx", sheet_name = hojas_350)
    DF_SB_350_CENTRAL = DF_SB_350["CENTRAL"]
    DF_SB_350_AT = DF_SB_350["AT"]
    DF_SB_388 = pd.read_excel(f"{directorio_SB}388 - SERVICIOS BASICOS - MCH.xlsx", sheet_name="SERVICIOS BASICOS")

    DF_PROV_311 = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="311")
    DF_SUBSIDIOS_311 = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="Subsidios")

    DF_PROV_330 = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="330")
    DF_PROV_330_CORREO = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="Correo Argentino" )
    DF_PROV_330_SEGUROS = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="Seguros" )
    DF_PROV_350_LA_CENTRAL = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "LA - CENTRAL")
    DF_PROV_350_LA_AT = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "LA - AT")
    DF_PROV_350_OC = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "OC - CENTRAL")
    DF_PROV_350_OC_AT = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "OC - AT")
    DF_PROV_388 = pd.read_excel(f"{directorio_PROV}388 - PROVEEDORES.xlsx", sheet_name = "Compilado")


    ejecucion_311_prov = {'nombre_archivo_salida' : f'{directorio_script}\\PROV - 311.xlsx',
                            'data_frame' : [DF_PROV_311, DF_SUBSIDIOS_311],
                            'hojas' : ['311', 'Subsidios'],
                            'data_frame_comparacion' : DF_SAF_311,
                            'columna_expediente' : ['EXPEDIENTE PAGADOR','EXPEDIENTE PAGADOR']    
                        }
    ejecucion_330_prov = {'nombre_archivo_salida' : f'{directorio_script}\\PROV - 330.xlsx',
                            'data_frame' : [DF_PROV_330, DF_PROV_330_CORREO, DF_PROV_330_SEGUROS],
                            'hojas' : ['330', '330 Correo', '330 Seguros'],
                            'data_frame_comparacion' : DF_SAF_330,
                            'columna_expediente' : ['EXPEDIENTE PAGADOR','EXPEDIENTE PAGADOR', 
                            'EXPEDIENTE PAGADOR']    
                        }
    ejecucion_350_prov = {'nombre_archivo_salida' : f'{directorio_script}\\PROV - 350.xlsx',
                            'data_frame' : [DF_PROV_350_LA_CENTRAL,
                            DF_PROV_350_LA_AT, DF_PROV_350_OC, DF_PROV_350_OC_AT],
                            'hojas' : ['350 LA CENTRAL','350 LA AT', '350 OC CENTRAL', '350 OC AT'],
                            'data_frame_comparacion' : DF_SAF_350,
                            'columna_expediente' : ['EXPEDIENTE PAGADOR','EXPEDIENTE PAGADOR', 
                            'EXPEDIENTE PAGADOR', 'EXPEDIENTE PAGADOR']    
                        }
    ejecucion_388_prov = {'nombre_archivo_salida' : f'{directorio_script}\\PROV - 388.xlsx',
                            'data_frame' : [DF_PROV_388],
                            'hojas' : ['388'],
                            'data_frame_comparacion' : DF_SAF_388,
                            'columna_expediente' : ['EXPEDIENTE PAGADOR']    
                        }
    
    ejecucion_del_codigo(**ejecucion_311_prov)
    ejecucion_del_codigo(**ejecucion_330_prov)
    ejecucion_del_codigo(**ejecucion_350_prov)
    ejecucion_del_codigo(**ejecucion_388_prov)

    
    
    #Se exportan los resultados de las planillas de SERVICIOS BASICOS 
    ejecucion_311_SB = {'nombre_archivo_salida' : f'{directorio_script}\\SB - 311.xlsx',
                            'data_frame' : [DF_SB_311],
                            'hojas' : ['311'],
                            'data_frame_comparacion' : DF_SAF_311,
                            'columna_expediente' : ['EXPEDIENTE PAGADOR']}
    
    ejecucion_330_SB = {'nombre_archivo_salida' : f'{directorio_script}\\SB - 330.xlsx',
                            'data_frame' : [DF_SB_330],
                            'hojas' : ['330'],
                            'data_frame_comparacion' : DF_SAF_330,
                            'columna_expediente' : ['EXPEDIENTE PAGADOR']}

    ejecucion_350_SB = {'nombre_archivo_salida' : f'{directorio_script}\\SB - 350.xlsx',
                            'data_frame' : [DF_SB_350_CENTRAL, DF_SB_350_AT],
                            'hojas' : ['350 Central', '350 AT'],
                            'data_frame_comparacion' : DF_SAF_350,
                            'columna_expediente' : ['EXPEDIENTE PAGADOR', 'EXPEDIENTE PAGADOR']}
    ejecucion_388_SB = {'nombre_archivo_salida' : f'{directorio_script}\\SB - 388.xlsx',
                            'data_frame' : [DF_SB_388],
                            'hojas' : ['388'],
                            'data_frame_comparacion' : DF_SAF_388,
                            'columna_expediente' : ['EXPEDIENTE PAGADOR']}

    ejecucion_del_codigo(**ejecucion_311_SB)
    ejecucion_del_codigo(**ejecucion_330_SB)
    ejecucion_del_codigo(**ejecucion_350_SB)
    ejecucion_del_codigo(**ejecucion_388_SB)    

    print(f"{50*'*'}")
    print(f"Finalizó la exportación de documentos")
    print(f"{50*'*'}")
    
