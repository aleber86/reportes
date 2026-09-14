# -*- coding: utf-8 -*-


import numpy as np
import pandas as pd
import re
import time
from zipfile import ZipFile
from modulo_de_funciones import (id_tram_space_norm, group_dupl, join_values, second_lookup,)


def deteccion_de_expedientes(DF_IN : pd.DataFrame, DF_COMP : pd.DataFrame, column_1 : str = "EXPEDIENTE N°" ,
              column_2 : str = "N° EXPEDIENTE PAGO", nombre_columna : str = "En Planillas"):

    """
    La función detecta expedientes que se encuentran en otras planillas, representadas mediante DataFrames.

    Args:
        DF_IN : DataFrame donde se ejecuta la búsqueda utilizando la columna 'column_1'
        column_1 : Nombre de la columna en la cual se ejecuta la búsqueda del DataFrame de ingreso, DF_IN
        DF_COMP : DataFrame de comparación en el cual se buscan los elementos, utilizando 'column_2'
        column_2 : Nombre de la columna en la cual se comparan del DataFrame de ingreso, DF_COMP
        nombre_columna : Nombre de la columna que se agrega al ejecutar la función

    Returns:
        Devuelve el DataFrame de ingreso, DF_IN, con la columna 'nombre_columna' agregada informando si
        el valor en la 'column_1' se encuentra en la planilla representada por el DataFrame DF_COMP, cuyo
        valor se encuentra en la column_2. En caso positivo la celda se puebla con 'SI'; por el contrario
        la celda queda vacía.
    """
   
    DF_IN[column_1] = DF_IN.apply(id_tram_space_norm, axis=1, args=(column_1,)).copy()
    DF_COMP = DF_COMP[[column_2]].drop_duplicates().dropna().copy()
    DF_COMP[column_2] = DF_COMP.apply(id_tram_space_norm, axis=1, args=(column_2,)).copy()
    if not nombre_columna in DF_IN.columns.to_list():
        DF_IN[nombre_columna] = DF_IN.apply(lambda _ : np.nan, axis=1).astype("string")

   
    mask_ = DF_IN[nombre_columna].isna()
    for idx in DF_IN.index[mask_]:
        text = DF_IN.at[idx, column_1]
        get_me = DF_COMP[column_2].str.contains(text, regex=False)
        if len(DF_COMP[get_me])>0:
            DF_TO_USE = DF_COMP[get_me].copy()

            DF_IN.at[idx, nombre_columna] = "SI"
    return DF_IN


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
    ARCHIVO = "OneDrive_2026-09-14.zip"
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
    

    
    #DF_SB_350_CENTRAL = pd.read_excel(f"{directorio_SB}350 - SERVICIOS BASICOS - TRABAJO.xlsx", sheet_name = "CENTRAL")
    #DF_SB_350_AT = pd.read_excel(f"{directorio_SB}350 - SERVICIOS BASICOS - TRABAJO.xlsx", sheet_name = "AT")

    #DF_PROVEEDORES_UNIFICADO = pd.read_excel("UNIFICADO PROVEEDORES.xlsx", sheet_name="Compilado Total")
    
    #DF_SAF_311_PROV = DF_PROVEEDORES_UNIFICADO[DF_PROVEEDORES_UNIFICADO["SAF"]==311].copy()
    #DF_SAF_330_PROV = DF_PROVEEDORES_UNIFICADO[DF_PROVEEDORES_UNIFICADO["SAF"]==330].copy()
    #DF_SAF_350_PROV = DF_PROVEEDORES_UNIFICADO[DF_PROVEEDORES_UNIFICADO["SAF"]==350].copy()
    #DF_SAF_388_PROV = DF_PROVEEDORES_UNIFICADO[DF_PROVEEDORES_UNIFICADO["SAF"]==388].copy()


    hojas_SAF = ["SAF 311", "SAF 330", "SAF 350", "SAF 388"]
    DF_SAFS = pd.read_excel("Reporte_PG_PRE_SG_311_341.xlsx", skiprows=4, sheet_name=hojas_SAF)
    DF_SAF_311 = DF_SAFS["SAF 311"]
    DF_SAF_330 = DF_SAFS["SAF 330"]
    DF_SAF_350 = DF_SAFS["SAF 350"]
    DF_SAF_388 = DF_SAFS["SAF 388"]
    #DF_SAF_311 = pd.read_excel("Reporte_PG_PRE_SG_311_341.xlsx", skiprows=4, sheet_name="SAF 311")
    #DF_SAF_330 = pd.read_excel("Reporte_PG_PRE_SG_311_341.xlsx", skiprows=4, sheet_name="SAF 330")
    #DF_SAF_350 = pd.read_excel("Reporte_PG_PRE_SG_311_341.xlsx", skiprows=4, sheet_name="SAF 350")
    #DF_SAF_388 = pd.read_excel("Reporte_PG_PRE_SG_311_341.xlsx", skiprows=4, sheet_name="SAF 388")

    #Descomentar el bloque en caso de buscar en ejercicios anteriores a 2026
    """
    #Archivos de origen historico
    DF_SAF_388_HIST = pd.read_excel("Reporte_311_341.xlsx", skiprows=4, sheet_name="SAF 388")
    DF_SAF_350_HIST = pd.read_excel("Reporte_311_341.xlsx", skiprows=4, sheet_name="SAF 350")
    DF_SAF_330_HIST = pd.read_excel("Reporte_311_341.xlsx", skiprows=4, sheet_name="SAF 330")
    DF_SAF_311_HIST = pd.read_excel("Reporte_311_341.xlsx", skiprows=4, sheet_name="SAF 311")
    #Agergado a los valores actuales
    DF_SAF_388 = pd.concat([DF_SAF_388_HIST, DF_SAF_388])
    DF_SAF_350 = pd.concat([DF_SAF_350_HIST, DF_SAF_350])
    DF_SAF_330 = pd.concat([DF_SAF_330_HIST, DF_SAF_330])
    DF_SAF_311 = pd.concat([DF_SAF_311_HIST, DF_SAF_311])
    

    DF_DIGEST_311 = execute(DF_SAF_311_PROV, DF_SAF_311, "EXPEDIENTE PAGADOR",forget=False)
    DF_DIGEST_330 = execute(DF_SAF_330_PROV, DF_SAF_330, "EXPEDIENTE PAGADOR",forget=False)
    DF_DIGEST_350 = execute(DF_SAF_350_PROV, DF_SAF_350, "EXPEDIENTE PAGADOR",forget=False)
    DF_DIGEST_388 = execute(DF_SAF_388_PROV, DF_SAF_388, "EXPEDIENTE PAGADOR",forget=False)
    
    #Stack vertical para la exposición de un solo DataFrame como resultado
    DF_DIGEST_FULL = pd.concat([DF_DIGEST_311, DF_DIGEST_330, DF_DIGEST_350, DF_DIGEST_388])
    
    #Se obtienen las columnas de interés, tendiendo en cuenta que el proceso de búsqueda produjo
    #valores de expedientes 'normalizados; en la realidad sus contrapartes son NO normalizadas
    DF_DIGEST_TO_FILE = DF_DIGEST_FULL[["EXPEDIENTE__SIN__NORMALIZAR", "SG(auto)", "PRE(auto)",
                                        "PG(auto)", "Fecha de Pago"]].copy()

    #Reducción de expedientes de salida; se obtienen solamente aquellos que poseen valores
    #no nulos en las columnas de interés mediante una máscara
    mask_full = ((~DF_DIGEST_TO_FILE["EXPEDIENTE__SIN__NORMALIZAR"].isna())& \
                ((~DF_DIGEST_TO_FILE["SG(auto)"].isna()) | (~DF_DIGEST_TO_FILE["PRE(auto)"].isna()) | (~DF_DIGEST_TO_FILE["PG(auto)"].isna())))

    
    DF_DIGEST_TO_FILE = DF_DIGEST_TO_FILE[mask_full].copy()

    #Se exportan los resultados de la planilla UNIFICADO
    with pd.ExcelWriter("PROV-FULL.xlsx") as  writer:
        DF_DIGEST_TO_FILE.to_excel(writer, sheet_name="SG_PRE_PG_UNIFICADO", index=False)

    """


        
    DF_PROV_311 = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="311")
    DF_SUBSIDIOS_311 = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="Subsidios")
    
    DF_PROV_330 = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="330")
    DF_PROV_330_CORREO = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="Correo Argentino" )
    DF_PROV_330_SEGUROS = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="Seguros" )
    DF_PROV_350_LA_CENTRAL = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "LA - CENTRAL")
    DF_PROV_350_LA_AT = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "LA - AT")
    DF_PROV_350_OC = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "OC - CENTRAL")
    DF_PROV_350_OC_AT = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "OC - AT")
    with pd.ExcelWriter("PROV - 330.xlsx") as writer:
        
        res = execute(DF_PROV_330, DF_SAF_330, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 330 PROVEEDORES", index=False)
        res = execute(DF_PROV_330_CORREO, DF_SAF_330, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 330 CORREO", index=False)
        res = execute(DF_PROV_330_SEGUROS, DF_SAF_330, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 330 SEGUROS", index=False)
        
        #res = execute(DF_SAF_330_PROV, DF_SAF_330, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 330 PROVEEDORES", index=False)
    
    with pd.ExcelWriter("PROV - 350.xlsx") as writer:
        
        res = execute(DF_PROV_350_LA_CENTRAL, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 LA - CENT", index=False)
        res = execute(DF_PROV_350_LA_AT, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 LA - AT", index=False)
        res = execute(DF_PROV_350_OC, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 OC CENTRAL", index=False)
        res = execute(DF_PROV_350_OC_AT, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 OC AT", index=False)
        
        #res = execute(DF_SAF_350_PROV, DF_SAF_350, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 350 LA - CENT", index=False)
        
    with pd.ExcelWriter("PROV - 311.xlsx") as writer:
        
        res = execute(DF_PROV_311, DF_SAF_311, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 311 PROVEEDORES", index=False)
        res = execute(DF_SUBSIDIOS_311, DF_SAF_311)
        res.to_excel(writer, sheet_name="SAF 311 SUBSIDIOS", index=False)
        
        #res = execute(DF_SAF_311_PROV, DF_SAF_311, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 311 PROVEEDORES", index=False)
        
   
        

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

    """

    
    DF_PROV_311 = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="311" )
    DF_SUBSIDIOS_311 = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="Subsidios")
    
    DF_PROV_330 = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="330" )
    DF_PROV_330_CORREO = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="Correo Argentino" )
    DF_PROV_330_SEGUROS = pd.read_excel(f"{directorio_PROV}330 - PROVEEDORES.xlsx", sheet_name ="Seguros" )
    DF_PROV_350_LA_CENTRAL = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "LA - CENTRAL")
    DF_PROV_350_LA_AT = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "LA - AT")
    DF_PROV_350_OC = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "OC - CENTRAL")
    DF_PROV_350_OC_AT = pd.read_excel(f"{directorio_PROV}350 - PROVEEDORES.xlsx", sheet_name = "OC - AT")
    with pd.ExcelWriter("PROV - 330.xlsx") as writer:
        
        #res = execute(DF_PROV_330, DF_SAF_330, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 330 PROVEEDORES", index=False)
        #res = execute(DF_PROV_330_CORREO, DF_SAF_330, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 330 CORREO", index=False)
        #res = execute(DF_PROV_330_SEGUROS, DF_SAF_330, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 330 SEGUROS", index=False)
        
        res = execute(DF_SAF_330_PROV, DF_SAF_330, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 330 PROVEEDORES", index=False)
    
    with pd.ExcelWriter("PROV - 350.xlsx") as writer:
        
        #res = execute(DF_PROV_350_LA_CENTRAL, DF_SAF_350, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 350 LA - CENT", index=False)
        #res = execute(DF_PROV_350_LA_AT, DF_SAF_350, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 350 LA - AT", index=False)
        #res = execute(DF_PROV_350_OC, DF_SAF_350, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 350 OC CENTRAL", index=False)
        #res = execute(DF_PROV_350_OC_AT, DF_SAF_350, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 350 OC AT", index=False)
        
        res = execute(DF_SAF_350_PROV, DF_SAF_350, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 350 LA - CENT", index=False)
        
    with pd.ExcelWriter("PROV - 311.xlsx") as writer:
        
        #res = execute(DF_PROV_311, DF_SAF_311, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 311 PROVEEDORES", index=False)
        #res = execute(DF_SUBSIDIOS_311, DF_SAF_311)
        #res.to_excel(writer, sheet_name="SAF 311 SUBSIDIOS", index=False)
        
        res = execute(DF_SAF_311_PROV, DF_SAF_311, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 311 PROVEEDORES", index=False)
        
    with pd.ExcelWriter("PROV - 388.xlsx") as writer:
        res = execute(DF_SAF_388_PROV, DF_SAF_388, "EXPEDIENTE PAGADOR")
        res.to_excel(writer, sheet_name="SAF 388 PROVEEDORES", index=False)
        
        #res = execute(DF_PROV_311, DF_SAF_311, "EXPEDIENTE PAGADOR")
        #res.to_excel(writer, sheet_name="SAF 311 PROVEEDORES", index=False)
        #res = execute(DF_SUBSIDIOS_311, DF_SAF_311)
        #res.to_excel(writer, sheet_name="SAF 311 SUBSIDIOS", index=False)
        
        
        
    
   
    #DF_SAF_311 = pd.read_excel(f"{directorio_SB}311 - SERVICIOS BASICOS - NIÑEZ.xlsx")
    #DF_PROV_311 = pd.read_excel(f"{directorio_PROV}311 - PROVEEDORES.xlsx", sheet_name ="311" )
    """

    print(f"{50*'*'}")
    print(f"Finalizó la exportación de documentos")
    print(f"{50*'*'}")
    
