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

    

if __name__ == '__main__':

     
    directorio_SB = "BASES SERVICIOS BASICOS\\"
    directorio_PROV = "BASES PROVEEDORES\\"

    #********************************************************************************
    #ÚNICA LÍNEA A MODIFICAR, DE SER NECESARIO:
    ARCHIVO = "OneDrive_2026-09-28.zip"
    archivos = [ARCHIVO, f"{ARCHIVO.replace('.zip',' (1).zip')}"]
    #CAMBIAR EL NOMBRE DEL ARCHIVO DESCARGADO DESDE OneDrive
    #********************************************************************************
    for archivo_comprimido in archivos:
        with ZipFile(archivo_comprimido, 'r') as zipped:
            zipped.extractall()
    
    DF_SB_311 = pd.read_excel(f"{directorio_SB}311 - SERVICIOS BASICOS - NIÑEZ.xlsx")
    
    DF_SB_330 = pd.read_excel(f"{directorio_SB}330 - SERVICIOS BASICOS - EDUCACION.xlsx", sheet_name = "330")

    hojas_350 = ["CENTRAL", "AT"]
    DF_SB_350 =  pd.read_excel(f"{directorio_SB}350 - SERVICIOS BASICOS - TRABAJO.xlsx", sheet_name = hojas_350)
    DF_SB_350_CENTRAL = DF_SB_350["CENTRAL"]
    DF_SB_350_AT = DF_SB_350["AT"]

    
    
    hojas_SAF = ["SAF 311", "SAF 330", "SAF 350", "SAF 388"]
    DF_SAFS = pd.read_excel("Reporte_PG_PRE_SG_311_341.xlsx", skiprows=4, sheet_name=hojas_SAF)
    DF_SAF_311 = DF_SAFS["SAF 311"]
    DF_SAF_330 = DF_SAFS["SAF 330"]
    DF_SAF_350 = DF_SAFS["SAF 350"]
    DF_SAF_388 = DF_SAFS["SAF 388"]
    
    
        
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
    #DF_PROV_311_SEGUROS = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="Seguros")
    #DF_PROV_311_SEGUROS_VARIOS = pd.read_excel("SEGUROS.xlsx", sheet_name="Seguros")
    #-------------------------PRE-UNIFICACION

    #DF_SAF311_PREUNIFICACION = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="311 (Pre-unificacion)")
    #DF_SAF330_PREUNIFICACION = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="330 (Pre-unificacion)")

    with pd.ExcelWriter("PROV - 330.xlsx") as writer:
        
        res = execute(DF_PROV_330, DF_SAF_330, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 330 PROVEEDORES", index=False)
        res = execute(DF_PROV_330_CORREO, DF_SAF_330, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 330 CORREO", index=False)
        res = execute(DF_PROV_330_SEGUROS, DF_SAF_330, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 330 SEGUROS", index=False)
        #res = execute(DF_SAF330_PREUNIFICACION, DF_SAF_330, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="330 (Pre-unificacion)")
        

    
    with pd.ExcelWriter("PROV - 350.xlsx") as writer:
        
        res = execute(DF_PROV_350_LA_CENTRAL, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 LA - CENT", index=False)
        res = execute(DF_PROV_350_LA_AT, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 LA - AT", index=False)
        res = execute(DF_PROV_350_OC, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 OC CENTRAL", index=False)
        res = execute(DF_PROV_350_OC_AT, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 OC AT", index=False)
        

        
    with pd.ExcelWriter("PROV - 311.xlsx") as writer:
        
        res = execute(DF_PROV_311, DF_SAF_311, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 311 PROVEEDORES", index=False)
        res = execute(DF_SUBSIDIOS_311, DF_SAF_311, forget=True)
        res.to_excel(writer, sheet_name="SAF 311 SUBSIDIOS", index=False)
        #res = execute(DF_SAF311_PREUNIFICACION, DF_SAF_311, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="311 (Pre-unificacion)")
        #res = execute(DF_PROV_311_SEGUROS, DF_SAF_311 , "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="311 Seguros", index=False)
        #res = execute(DF_PROV_311_SEGUROS_VARIOS, DF_SAF_311 , "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="311 Seguros varios", index=False)
        

    with pd.ExcelWriter("PROV - 388.xlsx") as writer:
        
        res = execute(DF_PROV_388, DF_SAF_388, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 388 PROVEEDORES", index=False)   
   
        

    #Se exportan los resultados de las planillas de SERVICIOS BASICOS
    with pd.ExcelWriter("SB - 330.xlsx") as writer:
        res = execute(DF_SB_330, DF_SAF_330)
        res.to_excel(writer, sheet_name="SAF 330 SB", index=False)

    with pd.ExcelWriter("SB - 311.xlsx") as writer:
        res = execute(DF_SB_311, DF_SAF_311)
        res.to_excel(writer, sheet_name="SAF 311 SB", index=False)
    with pd.ExcelWriter("SB - 350.xlsx") as writer:
        res = execute(DF_SB_350_CENTRAL, DF_SAF_350)
        res.to_excel(writer, sheet_name="SAF 350 SB CENTRAL", index=False)
        res = execute(DF_SB_350_AT, DF_SAF_350)
        res.to_excel(writer, sheet_name="SAF 350 SB AT", index=False)


    print(f"{50*'*'}")
    print(f"Finalizó la exportación de documentos")
    print(f"{50*'*'}")
    
