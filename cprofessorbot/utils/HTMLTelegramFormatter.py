################################################################################
# Nombre: HTMLTelegramFormater.py
# Descripción: Especificación e implementación de la clase HTMLTelegramFormater
# Autor: Nicolás Cubero Torres
################################################################################

#	Enlaces de interés
# https://docs.python.org/2/library/htmlparser.html (documentación ooficial de HTML Parser, última visita: 19 de julio de 2019)
# [1] - https://core.telegram.org/bots/api#formatting-options # Lista de etiquetas HTML soportadas por la API "TelegramAPIBot" última visita: 29 de Julio
# [2] - https://www.w3schools.com/tags/ Lista completa de tags admitidos en HTML5 (última visita: 25 de Julio de 2019)
# https://www.ibiblio.org/pub/Linux/docs/LuCaS/Manuales-LuCAS/doc-curso-html/doc-curso-html/x4275.html utilidad del atributo target de la etiqueta base 25 de julio

# Módulos importados
import re
from collections import OrderedDict
from html.parser import HTMLParser

class HTMLTelegramFormatter(HTMLParser):

	"""
	Esta clase se construye a partir del parser HTML de HTMLParser incluídos
	en el módulo html.parser [1]

	Utilidad destinada a formatear código HTML y a extraer a partir de él,
	textos, imágenes, audios, vídeos, enlaces y etiquetas HTML admitidas por
	Telegram Bot API [2], obviando o reformateando el resto de elementos que no
	aporten ninguna utilidad o no sean soportados por Telegram Bot Api

	Esta utilidad concibe su funcionamiento como una máquina de estados que
	ejecuta las siguientes operaciones para cada etiqueta (tag) admitida en
	HTML 5 [3] atendiendo a la función que desempeñan en el documento de
	hipertexto.

	Además del conjunto de etiquetas soportadas por HTML 5 y en la mayoría de
	los navegadores web, esta utilidad da soporte a otras etiquetas "deprecated"
	o en desuso, que eran soportadas por anteriores versiones de HTML y XHTML
	pero que ya no son admitidas por HTML 5

	b: Se agrega el la etiqueta de apertura, el texto contenido en su
		cuerpo y la etiqueta de cierre en el grupo actual en el que se está
		extrayendo texto.
	em: Se agrega el la etiqueta de apertura, el texto contenido en su
		cuerpo y la etiqueta de cierre en el grupo actual en el que se está
		extrayendo texto.
	i: Se agrega el la etiqueta de apertura, el texto contenido en su
		cuerpo y la etiqueta de cierre en el grupo actual en el que se está
		extrayendo texto.
	strong: Se agrega el la etiqueta de apertura, el texto contenido en su
		cuerpo y la etiqueta de cierre en el grupo actual en el que se está
		extrayendo texto.
	u: Se agrega la etiqueta code de apertura, el texto contenido en su
		cuerpo y la etiqueta de cierre en el grupo actual en el que se está
		extrayendo texto.
	code: Se agrega el la etiqueta de apertura, el texto contenido en su
		cuerpo y la etiqueta de cierre en el grupo actual en el que se está
		extrayendo texto.
	kbd: Se agregan las etiquetas pre de apertura y cierre y el texto
		contenido en su cuerpo en el grupo actual en el que se está
		extrayendo texto.
	tt: Se agregan las etiquetas pre de apertura y cierre y el texto
		contenido en su cuerpo en el grupo actual en el que se está
		extrayendo texto. (desuso)
	mark: Se agregan las etiquetas code de apertura y cierre y el texto
		contenido en su cuerpo en el grupo actual en el que se está
		extrayendo texto.
	samp: Se agregan las etiquetas code de apertura y cierre y el texto
		contenido en su cuerpo en el grupo actual en el que se está
		extrayendo texto.
	var: Se agregan las etiquetas pre de apertura y cierre y el texto
		contenido en su cuerpo en el grupo actual en el que se está
		extrayendo texto.
	q: Se agrega el texto contenido en su cuerpo en el grupo actual en el
		 que se está extrayendo texto entre comillas.
	h1 a h6: El contenido de su cuerpo se agrega en un cuerpo aparte y se le
			añade las etiquetas de apertura y de cierre de "b"
	abbr: Los datos incluídos en su cuerpo se agrega sin más
	acronym: Los datos incluídos en su cuerpo se agrega sin más (desuso)
	bdi: Los datos incluídos en su cuerpo se agregan sin más
	bdo: Los datos incluídos en su cuerpo se agregan sin más
	big: Los datos incluídos en su cuerpo se agregan sin más
	blockquote: Los datos incluídos en su cuerpo se agregan sin más
	body: Los datos incluídos en su cuerpo se agregan sin más, al recibir la
			etiqueta de cierre, se eliminan cadenas vacías que pudieran haber
			sido colocadas al final
	center: Los datos incluídos en su cuerpo se agregan sin más (desuso)
	cite: Los datos incluídos en su cuerpo se agregan sin más
	data: Los datos incluídos en su cuerpo se agrega sin más
	dd: Los datos incluídos en su cuerpo se agrega sin más
	del: Los datos incluídos en su cuerpo se agrega sin más (o reemplazarlo por negrita o alguna cosa)
	dfn: Los datos incluídos en su cuerpo se agrega sin más
	dialog: Los datos incluídos en su cuerpo se agrega sin más
	figcaption: Los datos incluídos en su cuerpo se agrega sin más
	figure: Los datos incluídos en su cuerpo se agregan sin más
	font: Los datos incluídos en su cuerpo se agregan sin más
	html: Los datos incluídos en su cuerpo se agregan sin más
	ins: Los datos incluídos en su cuerpo se agregan sin más
	meter: Los datos incluídos en su cuerpo se agregan sin más
	nav: Los datos incluídos en su cuerpo se agregan sin más
	picture: Los datos incluídos en su cuerpo se agregan sin más
	s: Los datos incluídos en su cuerpo se agregan sin más
	small: Los datos incluídos en su cuerpo se agregan sin más
	strike: Los datos incluídos en su cuerpo se agregan sin más
	sub: Los datos incluídos en su cuerpo se agregan sin más
	summary: Los datos incluídos en su cuerpo se agregan sin más
	sup: Los datos incluídos en su cuerpo se agregan sin más
	thead: Los datos incluídos en su cuerpo se agregan sin más
	tbody: Los datos incluídos en su cuerpo se agregan sin más
	td: Los datos incluídos en su cuerpo se agregan sin más
	tfoot: Los datos incluídos en su cuerpo se agregan sin más
	th: Los datos incluídos en su cuerpo se agregan sin más
	time: Los datos incluídos en su cuerpo se agregan sin más
	article: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	aside: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	details: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	dl: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	dt: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	header: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	p: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	section: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	span: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	table: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	template: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	tr: Los datos incluídos en su cuerpo se agregan en un grupo aparte
	address: Se ignora la etiqueta y su cuerpo
	applet: Se ignora la etiqueta y su cuerpo
	datalist: Se ignora la etiqueta y su cuerpo
	button: Se ignora la etiqueta y su cuerpo
	canvas: Se ignora la etiqueta y su cuerpo
	colgroup: Se ignora la etiqueta y su cuerpo
	embed: Se ignora la etiqueta y su cuerpo
	fieldset: Se ignora la etiqueta y su cuerpo
	frame: Se ignora la etiqueta y su cuerpo
	frameset: Se ignora la etiqueta y su cuerpo
	head: Se ignora la etiqueta y su cuerpo
	input: Se ignora la etiqueta y su cuerpo
	label: Se ignora la etiqueta y su cuerpo
	legend: Se ignora la etiqueta y su cuerpo
	map: Se ignora la etiqueta y su cuerpo
	noscript: Se ignora la etiqueta y su cuerpo
	object: Se ignora la etiqueta y su cuerpo
	optgroup: Se ignora la etiqueta y su cuerpo
	option: Se ignora la etiqueta y su cuerpo
	output: Se ignora la etiqueta y su cuerpo
	param: Se ignora la etiqueta y su cuerpo
	progress: Se ignora la etiqueta y su cuerpo
	rp: Se ignora la etiqueta y su cuerpo
	rt: Se ignora la etiqueta y su cuerpo
	ruby: Se ignora la etiqueta y su cuerpo
	script: Se ignora la etiqueta y su cuerpo
	select: Se ignora la etiqueta y su cuerpo
	style: Se ignora la etiqueta y su cuerpo
	svg: Se ignora la etiqueta y su cuerpo
	textarea: Se ignora la etiqueta y su cuerpo
	title: Se ignora la etiqueta y su cuerpo TODO
	DOCTYPE: No se hace nada
	basefont: No se hace nada (desuso)
	area: No se hace nada
	base: No se hace nada [4]
	col: No se hace nada
	link: No se hace nada
	track: No se hace nada
	meta: No se hace nada
	hr: Comienza la escritura en un grupo de texto nuevo
	dir: Registrar el inicio de una lista no ordenada y su fin con la
		etiqueta de terminación
	ol: Registrar el inicio de una lista ordenada y su fin con la
		etiqueta de terminación
	ul: Registrar el inicio de una lista no ordenada y su fin con la
		etiqueta de terminación
	li: Agrega texto en un grupo aparte que comienza con una enumeración
		(si se ha abierto una lista ordenada) o con puntos (si se ha abierto
		algún tipo de lista no ordenada)
	iframe: Se agrega un objeto con la clave "link" y especificando como
			valor de dicha clave, la url proporcionada en la etiqueta "src"
	a: Se agrega un objeto con la clave "link" y especificando como
			valor de dicha clave, la url proporcionada en la etiqueta "href"
	audio: Se agrega un objeto con la clave "audio" y especificando como
		valor de dicha clave la url proporcionada en la etiqueta "src" TODO
	img: Se agrega un objeto con la clave "imagen" y especificando como
		valor de dicha clave la url proporcionada en la etiqueta "src" TODO
	video: Se agrega un objeto con la clave "video" y especificando como
		valor de dicha clave la url proporcionada en la etiqueta "src" TODO
	source: Descargar el vídeo o audio o lo que se vea TODO
	bd: Se agrega un salto de línea
	wbr: Se agrega un salto de línea

	Atributos
	-----------

	data: list de str
		Lista de textos compatibles con el formato permitido por
		Telegram.ParseMode.html

	log: manejador de log
		Manejador de entradas de log para realizar escrituras sobre él

	Métodos:
	-----------

	feed: str
		Permite ejecutar el parseo del código HTML pasado como argumento.
		El resultado, se almacena en el atributo data.
		Nota: Este método es heredado de la superclase

	Raise:
	-----------
	ValueError: Cuando se encuentra alguna incoherencia sintáctica en el código
	html proporcionado con feed


	Enlaces de interés:
	-----------
	[1] - https://docs.python.org/2/library/htmlparser.html (documentación
			oficial de HTML Parser, última visita: 19 de julio)
	[2] - https://core.telegram.org/bots/api#formatting-options # Lista de
			etiquetas HTML soportadas por la API "TelegramAPIBot"
			última visita: 29 de Julio
	[3] - https://www.w3schools.com/tags/ Lista completa de tags admitidos en
			HTML5 (última visita: 25 de Julio)
	[4] - https://www.ibiblio.org/pub/Linux/docs/LuCaS/Manuales-LuCAS/doc-curso-html/doc-curso-html/x4275.html
			utilidad del atributo target de la etiqueta base 25 de julio

	"""

	def __init__(self, log=None):
		super(HTMLTelegramFormatter, self).__init__()

		self.__data = []		#	Conjuntos de texto extraídos
		self.__links = []		# Conjuntos de links leídos
		self.__tag_locker = [] 	#	Pila de tags inhabilitadores de recopilación
		self.__enum = []		#	Mantener la enumeración de las listas
		self.__base_url = ''	#	URL base a considerar
		self.__log = log		#	Manejador de entradas log
		#	Quizás sería bueno que sólo se admitieran páginas en HTML 5

	def handle_starttag(self, tag, attrs):

		if tag in ('head', 'script', 'address', 'applet', 'object', 'embed',
					'canvas', 'button', 'colgroup', 'datalist', 'fieldset',
					'frame', 'frameset', 'input', 'label', 'legend', 'map',
					'noscript', 'optgroup', 'option', 'output', 'param', 'rp',
					'rt', 'ruby', 'style', 'textarea'):
			#	Se apila la etiqueta que inhabilita la recolección de datos
			#	del documento de hipertexto
			self.__tag_locker.append(tag)

		elif tag in ('a', 'iframe'):
			#	Se encuentra un link
			for attr in attrs:
				if attr[0] in ('href', 'src'):
					self.__links.append(attr[1])

		elif tag == 'img':
			return

			#	Se encuentra una imagen y se ignora
			for attr in attrs:
				if attr[0] == 'src':
					self.__data.append({'imagen': attr[1]})

		elif tag in ('b', 'i', 'em', 'u', 'strong', 'big', 'tt', 'kbd', 'mark',
						'samp', 'var'):

			#	Sustituir etiquetas por etiquetas válidas para Telegram
			if tag in ('tt', 'kbd'):
				tag = 'pre'
			elif tag == 'big':
				tag = 'b'
			elif tag in ('mark', 'samp', 'var', 'u'):
				tag = 'code'

			#	Etiqueta letra en negrita, cursiva, etc
			if not (self.__data and isinstance(self.__data[-1], str)):
				self.__data.append('<%s>' % tag)
			else:
				self.__data[-1] += '<%s>' % tag

		elif tag == 'q':

			if not (self.__data and isinstance(self.__data[-1], str)):
				self.__data.append('"')
			else:
				self.__data[-1] += '"'

		elif tag in ('p', 'div', 'spam', 'article', 'aside', 'blockquote', 'tr',
						'details', 'dl', 'dt', 'section',
						'table', 'template') and not (self.__data and
						isinstance(self.__data[-1], str) and
						re.match('^(· |([0-9]+\.)+[0-9]* )?$',
							self.__data[-1])):
			self.__data.append('')

		elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
			#	Poner el texto aparte y en negrita
			if (not self.__data or not isinstance(self.__data[-1], str) or
														self.__data[-1] != ''):
				self.__data.append('<b>')
			else:
				self.__data[-1] += '<b>'

		elif tag == 'tc':
			if not self.__data:
				self.__data.append('')

			elif isinstance(self.__data[-1], str) and self.__data[-1]:
				#	Añadir espacio para separar cada columna de las tablas
				#	en los otros casos no es conveniente añadirlo
				self.__data[-1] += ' '

		elif tag in ('br', 'wbr'):

			if not (self.__data and isinstance(self.__data[-1], str)):
				self.__data.append('\n')
			else:
				self.__data[-1] += '\n'

		elif tag == 'hr' and (not self.__data or
						(isinstance(self.__data[-1], str) and self.__data[-1])):
			self.__data.append('')

		elif tag in ('dir', 'ul'):
			self.__enum.append(None)

		elif tag == 'ol':
			self.__enum.append(1)

		elif tag == 'li':
			if not self.__enum:
				if self.__log:
					self.__log.warning('etiqueta "li" encontrada fuera de lista')
				return

			#	Para las lista no ordenadas, se añade "·" al principio del
			#	grupo del texto, mientras que para las listas ordenadas, se
			#	añade los índices apilados en "__enum" separados por puntos,
			if self.__enum[-1] == None:
				index = '· '
			else:
				index = '.'.join([str(k) for k in self.__enum]) + '. '
				self.__enum[-1] += 1

			#	Agregar el índice (index) al inicio del texto
			if (not (self.__data and isinstance(self.__data[-1], str)) or
														self.__data[-1]):
				self.__data.append(index)
			else:
				self.__data[-1] += index

		elif tag == 'audio':
			pass

		elif tag == 'img':
			pass

		elif tag == 'source':
			pass

		elif tag == 'video':
			pass

	def handle_data(self, data):

		if not self.__tag_locker:
			#	Sólo se recopila si no se entá dentro de un tag
			#	carente de interés, e.g: head, script, applet

			#	Eliminar saltos de línea y espacios múltiples
			data = re.sub('[ \n\r]+', ' ', data)

			if re.match('^[ \n\r]*$', data):
				#	No se almacenan los textos inservibles
				return

			if self.__data and isinstance(self.__data[-1], str):
				self.__data[-1] += data

	def handle_endtag(self, tag):

		if tag in ('head', 'script', 'address', 'applet', 'object', 'embed',
					'canvas', 'button', 'colgroup', 'datalist', 'fieldset',
					'frame', 'frameset', 'input', 'label', 'legend', 'map',
					'noscript', 'optgroup', 'option', 'output', 'param', 'rp',
					'rt', 'ruby', 'style', 'template', 'textarea'):

			if not self.__tag_locker or not self.__tag_locker[-1] == tag:
				if self.__log:
					self.__log.warning('Encontrada etiqueta "{}" de cierre'\
												' inesperadamente'.format(tag))
				return

			#	Desapilar las etiquetas
			self.__tag_locker.pop()

		elif tag in ('b', 'i', 'em', 'u', 'strong', 'big', 'tt', 'kbd', 'mark',
																'samp', 'var'):

			#	Sustituir etiquetas por etiquetas válidas para Telegram
			if tag in ('tt', 'kbd', 'var'):
				tag = 'pre'
			elif tag == 'big':
				tag = 'b'
			elif tag in ('mark', 'samp'):
				tag = 'code'

			if not (self.__data and isinstance(self.__data[-1], str)):
				if self.__log:
					self.__log.warning('Encontrada etiqueta "{}" de cierre'\
												' inesperadamente'.format(tag))
				return

			#	Etiqueta letra en negrita, cursiva, etc
			self.__data[-1] += '</%s>' % tag

		elif tag == 'q':

			if not (self.__data and isinstance(self.__data[-1], str)):
				if self.__log:
					self.__log.warning('Encontrada etiqueta "{}" de cierre'\
												' inesperadamente'.format(tag))
				return

			#	Colocar el texto contenido en la etiqueta entre comillas
			self.__data[-1] += '"'

		elif tag in ('p', 'div', 'spam', 'article', 'aside', 'blockquote', 'tr',
							'details', 'dl', 'dt', 'section',
							'table', 'template') and not (self.__data and
							isinstance(self.__data[-1], str) and
							not self.__data[-1]):
			self.__data.append('')

		elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):

			if not (self.__data and isinstance(self.__data[-1], str)):
				if self.__log:
					self.__log.warning('Encontrada etiqueta "{}" de cierre'\
												' inesperadamente'.format(tag))
				return

			self.__data[-1] += '</b>'
			self.__data.append('')

		elif tag in ('dir', 'ul'):
			if not self.__enum or self.__enum[-1] != None:
				if self.__log:
					self.__log.warning('Encontrada etiqueta "{}" de cierre'\
												' inesperadamente'.format(tag))
				return

			#	Eliminar último None de la lista __enum
			self.__enum.pop()

		elif tag == 'ol':
			if not self.__enum or self.__enum[-1] == None:
				if self.__log:
					self.__log.warning('Encontrada etiqueta "{}" de cierre'\
												' inesperadamente'.format(tag))
				return

			#	Eliminar último número de la lista __enum
			self.__enum.pop()

		elif tag == 'li':
			self.__data.append('')

		elif tag == 'body' and ( self.__data and not self.__data[-1]):
			#	Eliminar alguna cadena vacía colocada al final
			self.__data.pop()

	def clear(self):
		"""Permite vaciar la lista de datos
		"""
		self.__data.clear()
		self.__links.clear()

	@property
	def data(self):
		return self.__data

	@property
	def links(self):
		return self.__links
