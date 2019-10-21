# -*- coding: utf-8 -*-
###############################################################################
# Programa: main.py
# Autor: Nicolás Cubero Torres
# Descripción: Script principal (main) del sistema servidor C-ProfessorBot
#				desarrollado como Trabajo de Fin de Grado y que inicia la
#				ejecución del sistema servidor
# Uso: python3 main.py -c <fichero de configuración> [--debug]
# Opciones:
#		- c | --configuration_file: Permite especificar el fichero JSON que
#				constrituye el fichero de configuración
#		--debug: Habilita el modo de depuración del servidor
###############################################################################

""" Módulos importados """
import argparse
import sys
import os
import cprofessorbot

""" Entrada de datos """
parser = argparse.ArgumentParser(
							description='Sistema servidor de C-ProfessorBot')

#	Parámetros obligatorios
parser.add_argument('-c','--config_file', nargs='?', type=str, required=True,
					action='store',
					help='Fichero de configuración JSON que contiene los'\
							' parámetros necesarios para la ejecución del'\
							' servidor. Introducir el comando sin valor para'\
							' generar una plantilla',
					const='')

#	Parámetros opcionales
parser.add_argument('--debug', action='store_true',
						help='Habilitar el modo de depuración del servidor')


# Parseo de argumentos
args = parser.parse_args(sys.argv[1:])

# Extracción de datos
config_file = args.config_file
debug = args.debug


""" Cuerpo del programa """
#	No se especifica fichero de configuración y se almacena un fichero
#	con parámetros por defecto
if config_file == '':

	#	Plantilla por defecto que se guarda
	try:
		cprofessorbot.BotServer.save_config_file_template(
											os.getcwd()+'/config_file.json')
	except Exception as e:
		print(('Error al guardar la plantilla del fichero de configuración: %s'%
				str(e)), file=sys.stderr)

		sys.exit(-1)

	print(('Se ha generado una plantilla del fichero de configuración en %s' %
											os.getcwd()+'/config_file.json'))
	sys.exit(0)

try:
	#	Crear el servidor
	server = cprofessorbot.BotServer(config_file, debug)

	#	Iniciar el funcionamiento del servidor
	server.start()
except Exception as e:
	print('Error en la ejecución del servidor: %s' % str(e), file=sys.stderr)
	sys.exit(-1)
