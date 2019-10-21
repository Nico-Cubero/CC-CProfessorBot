################################################################################
# Nombre: question_parser.py
# Descripción: Módulo con diversas funciones útiles para el parseo de texto
#				que contiene preguntas y respuestas
# Autor: Nicolás Cubero Torres
################################################################################

#	Enlaces de interés
# https://2.python-requests.org/en/master/
# Documentación oficial de requests (última visita: 10 de Septiembre de 2019)

#	Módulos importados
import re
import requests
from cprofessorbot.utils import HTMLTelegramFormatter
from cprofessorbot.nlu import processRequest
from cprofessorbot.utils import percentile
#  pip install requests

class QuestionParser:

	"""Utilidad encargada de parsear el contenido de un sitio web y obtener
		todos los Conceptos Teóricos presentes en el mismo.
	"""

	def __evaluate_questions_answers(text: list):

		if type(text) is not list:
			raise ValueError('"text" no es una lista')

		#	A cada texto almacenado en text se le asignará una punctuación
		line_score = [0]*len(text)

		for i in range(len(text)):

			#	Desechar los links, imágenes, vídeos, audios, etc
			if type(text[i]) is not str:
				continue

			#	Para cada texto, se evalúan diferentes características y
			#	formatos que se consideran propias de los enunciados que
			#	describen una pregunta: e.g. que estén numeradas, que el
			#	enunciado de la pregunta esté formateado: que esté escrito en
			#	negrita, que presente una fuente diferente, use encabezados, etc
			#	y se puntúa positivamente con el fin de identificar el formato
			#	de las preguntas de la urlproporcionada

			m = re.search(
	r'^[ \n\t\r]*([0-9\.\)]+[0-9\.\)]*)? *((<(b|strong)>).+(<\/\4>)(.*)|.+)',
																		text[i])

			if m:
				#	Evaluar las características del texto

				if m.group(1):
					#	La pregunta comienza con una enumeración
					#	1. Cómo se implementa un editor de texto. Se podría así
					line_score[i] += 1

				if m.group(3) and m.group(5):
					#	El texto que contiene la pregunta aparece formateado:
					#	negrita, cursiva, con una fuente diferente, encabezados,
					#	 etc. Ejemplo:
					#	<b>Cómo se implementa un editor de texto</b> Se hace así
					line_score[i] += 1

					if not m.group(6) and m.group(1):
						#	La pregunta no es seguida por ningún otro texto
						#	después del texto de la pregunta formateado. Sólo se
						#	puntúa si se cumple además la primera condición
						line_score[i] += 1

		return line_score

	def extract_questions_from_url(url: str, log=None, visited_url=None):

		"""Se encarga de ejecutar el algoritmo para la extracción de Conceptos
		Teóricos a partir del sitio web de la url pasada como parámetro

		Argumentos:
		-----------
		url: str
			URL del sitio web sobre el que se va a aplicar la extracción

		log: log
			Utilidad para el registro de entradas en el ficheros de bitácora,
			si se desea que se vayan escribiendo entradas sobre las operaciones
			que se realizan. Es opcional

		visited_url: set o None
			Listado de urls ya visitadas. Dejar en None
		"""

		if visited_url is None:
			visited_url = set()

		html_parser = HTMLTelegramFormatter(log)
		preguntas = []

		if log: log.info('Accediendo y analizando url: "%s" para'\
							' la extracción de preguntas y respuestas' % url)

		#	Tomar la página
		response = requests.get(url)

		if response.status_code < 200 or response.status_code >= 300:
			if log is not None: log.error('Error al hacer GET, código'\
									'de operación: "%d"' % response.status_code)
			return []	#	Devolver valor nulo

		else:
			if log is not None: log.info('Ejecutado GET con código de '\
									'operación: "%d"' % response.status_code)

		html = response.text

		#	Parsear la página
		html_parser.feed(html)

		if not html_parser.data:
			return []

		#	Puntuar cada texto en función de la posibilidad de ser pregunta o no
		line_score = QuestionParser.__evaluate_questions_answers(
															html_parser.data)
		max_score = percentile(line_score, 90)

		if max_score == 0 and sum(line_score)==0:
			return []	#	Devolver lista vacía

		#	Extraer preguntas y respuestas
		for i in range(len(line_score)):

			if line_score[i] >= max_score:

				#	Se ha encontrado alguna pregunta y se extrae
				m = re.search(r'^[ \n\t\r]*([0-9\.\)]+[0-9\.\)]*)? *((<([a-zA-Z0-9]+)>)(.+)(<\/\4>[\.:]*)(.*)|(.+[^ ])[\.:\?\!]*(.*))', html_parser.data[i]) #or re.search(r'^[ \n\t\r]*((<([a-zA-Z0-9]+)>) ?(<li>|[0-9\.\)]+)? ?(.+)(<\/\4>)(.*)|(.+[^ ])[\.:\?\!](.*))', html_parser.data[i])

				if m:

					#	Eliminar todas las etiquetas de la pregunta
					pr = m.group(5) if m.group(3) else m.group(8)
					pr = re.sub('<\/?[a-zA-Z0-9]+>', '', pr)

					new_pre = {
								'pregunta': pr,
								'respuesta': []
							}

					if m.group(3) and m.group(7) != '':
						new_pre['respuesta'] +=  m.group(7).split('\n')

					elif m.group(9) not in ('', None):
						new_pre['respuesta'] += m.group(9).split('\n')

					elif (i < len(line_score)-1 and
											line_score[i] == line_score[i+1]):

						#	Si no hay texto para la respuesta y el siguiente
						#	texto tiene la misma puntuación que el actual, el
						#	texto actual podría no ser una pregunta
						#	correctamente respondida

						continue

					preguntas.append(new_pre)

			elif preguntas:

				#	Todo lo demás se considera respuesta
				preguntas[-1]['respuesta'] += html_parser.data[i].split('\n')

		if log is not None: log.info('Final de análisis de url: "%s" '\
					'encontradas %d preguntas válidas' % (url, len(preguntas)))

		#	Ejecutar extracción en los subenlaces
		l_bar = url.rfind('/') #	Buscar la última "/" de la url

		if l_bar != -1 and len(url) >= 2 and url[l_bar-2] != ':':
			#	Comprobar que esta "/" no sea la que aparece tras el protocolo
			#	e.g: https://
			folder_url = url[:l_bar+1]
		else:
			folder_url = url

		for link in html_parser.links:

			if '#' in link:
				continue	# Salto dentro de la misma página, se ignora

			elif (re.match('^https?:', link) and not link.startswith(
															folder_url)):
				#	El enlace lleva a otra web diferente y se ignora
				continue

			elif len(link) > 2 and link.startswith('..'):
				#	El enlace lleva a la página anterior
				continue

			elif link[0] == '.' and len(link) > 1:
				new_url = folder_url + link[1:]

				if new_url in visited_url:
					continue
				else:
					visited_url.add(new_url)

				preguntas += (QuestionParser.extract_questions_from_url(
								new_url, log, visited_url))

			elif (link[0] == '/' and len(link) > 1):
				if folder_url.endswith('/'):
					folder_url = folder_url[:-1]

				new_url = folder_url + link

				if new_url in visited_url:
					continue
				else:
					visited_url.add(new_url)

				preguntas += QuestionParser.extract_questions_from_url(
								new_url, log, visited_url)

			elif (re.match('^[a-zA-Z]+:', link) and
											not re.match('^https?:', link)):
				#	El enlace emplea otro protocolo diferente a http
				#	o https como ftp, mailto, etc
				continue

			else:
				if not folder_url.endswith('/') and not link.startswith('/'):
					new_url = folder_url + '/' + link
				else:
					new_url = folder_url + link

				if new_url in visited_url:
					continue
				else:
					visited_url.add(new_url)

				preguntas += QuestionParser.extract_questions_from_url(
							new_url, log, visited_url)

		return preguntas
