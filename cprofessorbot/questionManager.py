################################################################################
#   Nombre: questionManager.py
#   Descripción: Especificación e implementación de la clase QuestionManager
#   Autor: Nicolás Cubero Torres
################################################################################

#   Módulos importados
import datetime
import os
import json
import re
from cprofessorbot.nlu import processRequest, QuestionParser
from cprofessorbot.botServerDAO import BotServerDAO
import logging

class QuestionManager:

	"""
	Utilidad destinada a gestionar todos los conceptos teóricos mantenidos por
	el sistema en su base de datos llevando a cabo todo el preprocesamiento de
	textos requeridos por el sistema.

	Atributos
	-----------
	bd_interface: BotServerDAO
		Interfaz de acceso a la base de datos

	base_directory: str
		Ruta al directorio base mantenido por el servidor
	"""

	def __init__(self, bd_interface: BotServerDAO, base_directory: str):

		self.__bd_interface = bd_interface  	#	Interfaz de acc a base datos
		self.__base_directory = base_directory	#	Directorio base del servidor

		#	Configurar el logging del sistema
		self.__log = logging.getLogger('cprofessorbot_log')

	def addQuestion(self, quest: dict):

		"""Permite añadir un nuevo Concepto Teórico a la base de datos

		Parámetros:
		-----------

		quest: dict
			Diccionario que contiene las siguientes claves:
			pregunta y respuesta

			El valor correspondiente a dichas claves es un str o list str
			con las preguntas y respuestas
		"""

		self.__log.debug('Iniciada la función "addQuestion" de'\
														' "QuestionManager"')

		#   Comprobar que todos los campos existen
		if ('pregunta' not in quest or
								not isinstance(quest['pregunta'], (str, list))):
			raise ValueError('"pregunta" debe de ser str o list str')

		if isinstance(quest['pregunta'], str):
			#	Introducir en una lista
			quest['pregunta'] = [quest['pregunta']]


		if ('respuesta' not in quest or
								not isinstance(quest['pregunta'], (str, list))):
			raise ValueError('"respuesta" debe de ser str o list str')

		if isinstance(quest['respuesta'], str):
			#	Introducir en una lista
			quest['respuesta'] = [quest['respuesta']]


		#	Introducir cada pregunta en la base de información
		id_concepto = None

		for p in quest['pregunta']:
			#	Se obtiene el resumen de la pregunta y la categoría semántica
			#	a la que pertenecen
			resumen_concepto, tipo = processRequest(p)

			#	Se toma la categoría semántica principal
			tipo = tipo[0] if isinstance(tipo, list) else tipo

			#	Si se introdujo una pregunta similar, se salta
			if self.__bd_interface.existsConcepto(res_preg=resumen_concepto,
													tipo=tipo):
				continue

			#	Añadir el concepto procesado a la base de datos
			id_concepto = self.__bd_interface.addConcepto(concepto=p,
											resumen_concepto=resumen_concepto,
											tipo=tipo,
											id_concepto=id_concepto)

		if id_concepto is None:
			self.__log.debug('Finalizada la función "addQuestion" de'\
														' "QuestionManager"')
			return

		#	Añadir y/o descargar los contenidos que constituyen la respuesta
		for c in quest['respuesta']:

			#	Comprobar que el dato es válido
			if not isinstance(c, str):
				raise ValueError('"respuesta" no contiene ninguna cadena válida')

			#	Es texto lo que se añade

			#	Cambiar los <, > y & que no se usen para etiquetas html
			#	ya que crean conflicto al emitir las respuestas
			c = re.sub('<(?!(\/?b>)|(\/?i>)|(\/?a>)|(\/?code>)|(\/?pre>))', r'&lt;', c)
			c = re.sub('(?<!<b)(?<!<\/b)(?<!<i)(?<!<\/i)(?<!<a)(?<!<\/a)(?<!<code)(?<!<\/code)(?<!<pre)(?<!<\/pre)>', r'&gt;', c)
			c = re.sub('&(?!(lt;)|(gt;)|(quot;))', r'&amp;', c)

			self.__bd_interface.addDatoTexto(
								id_concepto=id_concepto,
								fecha_creacion=datetime.datetime.now(),
								texto=c)

		self.__log.debug('Finalizada la función "addQuestion" de'\
														' "QuestionManager"')

	def ask(self, quest: str):

		"""Permite buscar una respuesta válida para una pregunta formulada

		Parámetros:
		-----------
		quest: str
			Pregunta para la cual se desea buscar una o varias respuestas
			válidas

		Devuelve:
			OrderedDict con el par id_dato y dato
			Donde dato contiene los siguientes valores:

			·tipo_dato: 'texto'
			·texto: str o list str
			 	Texto o textos a almacenar
		"""

		self.__log.debug('Iniciada la función "ask" de "QuestionManager"')

		#	Procesar respuesta para extraer concepto y buscar por él
		sum_concept, tipo = processRequest(quest)

		respuesta = self.__bd_interface.searchConcepto(sum_concept, tipo)

		self.__log.debug('Finalizada la función "ask" de "QuestionManager"')

		return respuesta

	def removeAllConcepts(self):

		"""Permite eliminar todas los Conceptos Teóricos de la base de datos
		"""

		#	Cambiar nombre
		self.__log.debug('Iniciada la función "removeAllConcepts" de'\
														' "QuestionManager"')

		#	Tomar el listado de archivos multimedia asociados a todos los
		#	conceptos y eliminarlos
		archivos = self.__bd_interface.listAllConceptosMultimediaFiles()

		if archivos is not None:

			for a in archivos:
				os.remove(a)

		#	Eliminar todos los datos de los contenidos teóricos de la bd
		self.__bd_interface.removeAllConceptos()

		self.__log.debug('Finalizada la función "removeAllConcepts" de'\
														' "QuestionManager"')

	def load_from_file(self, filename: str):

		"""Permite cargar los Conceptos Teóricos a partir de un fichero JSON

		filename: str
			Ruta relativa o absoluta al fichero JSON a cargar

			El formato del fichero JSON debe de estar formado por un array
			de objetos JSON los cuales presenten el formato del atributo "quest"
			de la función addQuestion
		"""

		self.__log.debug('Iniciada la función "load_from_file" de'\
														' "QuestionManager"')


		#	Cargar cada uno de los conceptos almacenados en el fichero JSON
		try:
			f = open(filename, 'r')
		except:
			raise ValueError('Error al abrir "%s"' % filename)

		#	Leer el fichero JSON con los datos
		conceptos = json.load(f)
		f.close()

		for concepto in conceptos:
			self.addQuestion(concepto)

		self.__log.debug('Finalizada la función "load_from_file" de "QuestionManager"')

	def load_from_url(self, url: str):

		"""Permite cargar los Conceptos Teóricos a partir del contenido
			de una url

		Parámetros:
		-----------
		url: str
			Dirección url del sitio web del que se desea extraer los Conceptos
			Teóricos
		"""

		self.__log.debug('Iniciada la función "load_from_url" de'\
														' "QuestionManager"')


		conceptos = QuestionParser.extract_questions_from_url(url, self.__log)

		for concepto in conceptos:
			self.addQuestion(concepto)

		self.__log.debug('Finalizada la función "load_from_url"'\
													' de "QuestionManager"')

		return conceptos
