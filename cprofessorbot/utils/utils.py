################################################################################
# Nombre: utils.py
# Descripción: Módulo con diversas funciones útiles
# Autor: Nicolás Cubero Torres
################################################################################

#	Módulos importados
import os
import os.path


def copyFile(source: str, destination: str):

	"""
	Permite copiar un archivo origen en otro destino

	Parámetros:
	-----------

	source : src
		Nombre de fichero del archivo de origen

	destination : src
		Nombre de fichero del archivo destino o del directorio en el que se
		desee ubicar
	"""

	#	Construir el nombre del fichero destino si se ha especificado un directorio
	if destination[-1] == '/':
		destination = destination + os.path.basename(source)

	#	Abrir el archivo origen que se va a a copiar
	src_file = open(source,'rb')

	#	Crear el archivo destino que contendrá la copia
	dst_file = open(destination, 'wb')

	#	Copiar cada byte del archivo source al destination
	byte = src_file.read(1)

	while byte != b'':
		dst_file.write(byte)		#	Escribir byte leído
		byte = src_file.read(1)		#	Leer nuevo byte

	src_file.close()
	dst_file.close()

	return destination

def percentile(data: list, perc: int):

	"""Permite calcular el percentil de un conjunto de datos pasados como
		argumento

	Parámetros:
	-----------
	data: list de float o int
		Conjunto de valores al cual se aplica el cálculo del percentil

	perc: int
		Percentil que se desea calcular
		Debe de contener un valor en el intervalo [0, 100]

	"""

	#	Citar el libro de estadística de Arturo y Roberto
	if type(data) is not list:
		raise ValueError('"data" debe de ser una lista')

	if type(perc) is not int:
		raise ValueError('"perc" debe de ser int')
	elif perc < 0 or perc > 100:
		raise ValueError('"perc" debe de estar comprendido entre 0 y 100')

	#	Ordenar la lista
	data = list(data)
	data.sort()

	#	Calcular el índica a tomar
	index = int(len(data)*perc//100)

	return data[index]

def removeDirectory(path: str):

	"""
	Permite eliminar un directorio y todo lo que haya en su interior

	Parámetros:
	-----------

	path: str
		Ruta del directorio
	"""

	if path[-1] == '/':
		path = path + '/'

	if os.path.isdir(path) == False:
		raise ValueError('No directory in "%s"' % path)

	for f in os.listdir(path):
		filename = path+f

		if os.path.isdir(filename):
			#	Borrar el contenido del directorio
			removeDirectory(filename+'/')

		elif os.path.exists(filename):
			#	Borrar el archivo
			os.remove(filename)

	#	Eliminar el directorio ahora vacío
	if not os.listdir(path):
		os.rmdir(path)
