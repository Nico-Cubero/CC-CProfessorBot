################################################################################
#   Nombre: speechHandler.py
#   Descripción: Especificación e implementación de la clase SpeechHandler
#   Autor: Nicolás Cubero Torres
################################################################################

# Módulos importados
import io
from collections import Iterable
from cprofessorbot.nlu.naturalLanguageProcessing_utils import preprocessTokenizeText

class SpeechHandler:

	"""
	Utilidad encargada de evaluar si un documento trata un tema válido o no y
	de aprender el vocabulario inherente al tema mediante un proceso de
	aprendizaje usando como patrones documentos que traten los temas a
	considerar válidos
	"""

	def __init__(self):

		self.__vocabulary = set() #	Vocabulario mantenido sobre los temas válidos

	def __fit_string(self, text: str):

		#	Preprocesar y tokenizar el texto
		text = preprocessTokenizeText(text)

		#	Introducirlo en el vocabulario
		for t in text:
			self.__vocabulary.add(t)

	def fit(self, documents: Iterable or str):

		"""Realiza el aprendizaje del vocabulario a partir de los textos
			del conjunto de documentos proporcionados

		Parámetros:
		-----------
		documents: str, colección de str
			texto o conjunto de textos a partir de los cuales se lleva a cabo
			el aprendizaje

		Devuelve:
		---------
			SpeechHandler. Objeto ya entrenado
		"""

		if isinstance(documents, io.IOBase):
			#	Se ha proporcionado un archivo y se procesa línea por línea

			for d in documents:
				self.__fit_string(d)

			documents.close()

		elif isinstance(documents, str):
			#	Se ha proporcionado una cadena
			self.__fit_string(documents)

		elif isinstance(documents, Iterable):
			#	Se ha proporcionado una lista, tupla, conjunto, etc

			for d in documents:
				self.__fit_string(d)

		else:
			raise ValueError('"document" no es str, descriptor de fichero u\
														objeto iterable válido')

		return self

	def save_vocabulary(self, filename):

		"""Permite almacenar el vocabulario aprendido en un fichero

		Parámetros:
		-----------
		filename: str
			Ruta del fichero donde se almacena el vocabulario
		"""

		#	Comrpobar los parámetros proporcionados
		if type(filename) is not str:
			raise ValueError('"filename" must be a path file')

		with open(filename, 'w') as f:
			#	Escribir el vocabulario en el fichero proporcionado
			f.write('\n'.join(self.__vocabulary))

	def evaluate(self, text: str):

		"""Ejecuta la evaluación del conjunto de palabras presentes
			que se hallan en el texto pasado como argumento.

		Argumentos:
		-----------
		text: str
			Texto a evaluar

		Devuelve:
			float o None. Valor comprendido entre 0 y 1 que indica el procentaje
			de palabras del texto pasado que están presentes en el vocabulario,
			donde 0 se corresponde con la presencia de palabras donde ninguna
			está contenida en el vocabulario y 1 cuando todas las palabras están
			contenidas en el vocabulario.

			Se devuelve None si el texto no incluye nada evaluable (como
			consecuencia de preprocesamiento)
		"""

		#	Comrpobar los parámetros proporcionados
		if type(text) is not str:
			raise ValueError('"text" must be a string')

		#	Preprocesar y tokenizar el texto
		text = preprocessTokenizeText(text)

		if not text:
			return None

		#	Contar el número de palabras que se encuentran en el vocabulario
		#	(pertenecen a los temas válidos)

		score = 0.0

		for i in range(len(text)):
			if text[i] in self.__vocabulary:
				#	La palabra está y se suma un punto
				score += 1.0


		#	Calcular promedio y devolverlo
		return score/len(text)
