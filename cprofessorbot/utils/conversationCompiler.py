################################################################################
#	Descripción: Especificación e implementación de la
#					utilidad ConversationCompiler.
#
#	Autor: Nicolás Cubero Torres
################################################################################

#	Módulos importados
import os.path
import time
import datetime
import mimetypes
import zipfile
import urllib
from cprofessorbot.utils.utils import copyFile, removeDirectory

class ConversationCompiler:

	"""
	Utilidad que permite generar un fichero comprimido donde se recopilan
	conversaciones con todos los datos pertinentes a las mismas y una
	página html para la visualización de dichas conversaciones

	Atributos
	-----------

	conversation_directory: str
		Ruta donde se almacenará el fichero comprimido de recopilación

	nombre_foro: str
		Nombre del Foro sobre el cual se va a realizar la recopilación

	fecha_inicio: datetime.datetime
		Fecha en la que se inicia la recopilación

	fecha_fin: datetime.datetime
		Fecha en la que se inicia la recopilación

	docente_solicitante: str
		Nombre del usuario docente que solicitó la recopilación

	lista_usuarios: list de str
		Lista con los nombres completos de los usuarios que
		aparecen en el foro docente

	Enlaces de interés:
	-------------------
	[1] - https://www.urlencoder.io/python/ Convertir caracteres de cualquier
		codificación a caracteres utf-8 según el formato admitidos en las URL
	"""

	###	Constantes ###
	__HTML_PREAMBLE = '''<!DOCTYPE html>
<html>
	<!-- Establecer el encabezado -->
	<head>
		<meta charset="UTF-8">
		<title>Conversación descargada</title>
		<meta name="description" content="Ejemplo de pantalla de conversación">
		<meta name="author" content="Nicolás Cubero Torres">
	</head>

	<style>

		/*Estilo del cuadro con info del grupo docente y de la recopilación*/
		.group_information {
			margin:0px auto;
			padding: 5px;
			background-color: #FFFFFF;
			width: 400px;
			box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
		}

		/*Estilo de los bocadillos de mensajes normales de alumnos*/
		.message_box {
			padding: 5px;
			padding-left: 10px;
			padding-right: 10px;
			background-color: #74C278;
			color: "";
			border-radius: 12px;
			min-width: 250px;
			float: left;
			clear: both;
		}

		.message_box:before {
			content: "";
			position: absolute;
			width: 0;
			height: 0;
			border-top: 15px solid transparent;
			border-bottom: 15px solid #74C278;
			border-right: 15px solid transparent;
			margin: -35px 0 0 5px;
		}

		.message_box:hover{
			background-color: #93D096;
		}

		.message_box:hover:before{
			border-bottom: 15px solid #93D096;
		}

		/*Estilo de los bocadillos de mensajes del asistente*/
		.message_box_bot {
			padding: 5px;
			padding-left: 10px;
			padding-right: 10px;
			background-color: #83C6E7;
			color: "";
			border-radius: 12px;
			min-width: 250px;
			float: right;
			clear: both;
		}

		.message_box_bot:before {
			content: "";
			position: absolute;
			width: 0;
			height: 0;
			float: right;
			border-top: 15px solid transparent;
			border-bottom: 15px solid #83C6E7;
			border-left: 15px solid transparent;
			margin: -35px 0 0 -15px;
		}

		/*Estilo de los bocadillos anunciadores de eventos*/
		.parent_evento_box {
			margin: 0 auto;
			/*min-width: 250px;*/
			float: center;
			clear: both;
		     	display: flex;
			align-items: center;
		     	justify-content: center;
		}


		.evento_box {
			content: "";
			padding: 5px;
			background-color: #FFFFFF;
			border-radius: 20px;
		}

		/*Estilo de los cuadros con contactos y localizaciones*/
		.contacto_box {
			padding: 5px;
			background-color: #E0E0E0;
			border-radius: 10px;
		}

		/*Estilo de los botones de documentos*/
		.documento_button {
			padding: 5px 10px;
			color: black;
			background-color: #F1F1F1;
			text-decoration: none;
			text-align: center;
			display: inline-block;
			cursor: pointer;
			box-shadow: 0 4px 4px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
		}

		.message_box_bot:hover {
		  background-color: #96CFEB;
		}

		.message_box_bot:hover:before {
			border-bottom: 15px solid #96CFEB;
		}

		/*Estilo de los bocadillos de mensajes enviados no permitidos*/
		.message_box_ban {
			padding: 5px;
			padding-left: 10px;
			padding-right: 10px;
			background-color: #C3C3C3;
			color: "";
			border-radius: 12px;
			min-width: 250px;
			float: left;
			clear: both;
		}

		.message_box_ban:before {
			content: "";
			position: absolute;
			width: 0;
			height: 0;
			border-top: 15px solid transparent;
			border-bottom: 15px solid #C3C3C3;
			border-right: 15px solid transparent;
			margin: -35px 0 0 5px;
		}

		/*Estilo de los bocadillos de mensajes de profesores*/
		.message_box_professor {
			padding: 5px;
			padding-left: 10px;
			padding-right: 10px;
			background-color: #FFD33E;
			color: "";
			border-radius: 12px;
			min-width: 250px;
			float: left;
			clear: both;
		}

		.message_box_professor:before {
			content: "";
			position: absolute;
			width: 0;
			height: 0;
			border-top: 15px solid transparent;
			border-bottom: 15px solid #FFD33E;
			border-right: 15px solid transparent;
			margin: -35px 0 0 5px;
		}

		.message_box_professor:hover {
			background-color: #FFE075;
		}

		.message_box_professor:hover:before {
			border-bottom: 15px solid #FFE075;
		}

		/*Cuadro de espacio entre bocadillo y bocadillo*/
		.space {
			padding: 12px;
			background-color: transparent;
			color: "";
			float: left;
			clear: both;
		}

		/*Estilo del nombre de usuario que envía un mensaje*/
		.name {
			color: black;
			font-weight: bold;
			font-size: 13pt;
			margin-bottom: 3pt;
		}

		/*Estilo del contenido del mensaje*/
		.content {
			color: white;
			font-size: 12pt;
		}

		/*Estilo de la fecha mostrada en los mensajes*/
		.date {
			color: grey;
		}

		/*Control del tamaño de la imagen*/
		img{
			max-height:500px;
			max-width:500px;
			height:auto;
			width:auto;
		}

		/*Control del tamaño de vídeo*/
		video {
			max-height:500px;
			max-width:500px;
			height:auto;
			width:auto;
		}

		/*Fondo y tipo de letra de la página*/
		body {
			background-color: #E5DDD5;
			font-family: cursive;
		}

		/*Estilo del cuadro que engloba a la leyenda de colores*/
		dl {
			padding: 5px;
			background-color: #FFFFFF;
			display: inline;
			box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
		}

		/*Estilo de cada elemento de la leyenda*/

		dt {
			display: inline;
			margin: 0;
		}

		dd {
			display: inline;
			margin: 7px;
		}

	</style>

	<!-- Cuerpo y contenido de la página -->
	<body>

	'''

	def __init__(self, conversation_directory: str, nombre_foro: str,
				fecha_inicio: datetime.datetime, fecha_fin: datetime.datetime,
				docente_solicitante: str, lista_usuarios: list):

		#	Comprobar que los tipos sean válidos
		if type(conversation_directory) is not str:
			raise ValueError('\"conversation_directory\" debe de ser str')

		if type(nombre_foro) is not str:
			raise ValueError('\"nombre_foro\" debe de ser str')

		if type(fecha_inicio) is not datetime.datetime:
			raise ValueError('\"fecha_inicio\" debe de ser de tipo '\
															'datetime.datetime')

		if type(fecha_fin) is not datetime.datetime:
			raise ValueError('\"fecha_fin\" debe de ser de tipo '\
															'datetime.datetime')

		if type(docente_solicitante) is not str:
			raise ValueError('\"docente_solicitante\" debe de ser str')

		if type(lista_usuarios) is not list:
			raise ValueError('\"lista_usuarios\" debe de ser list')
		else:
			for u in lista_usuarios:
				if type(u) is not str:
					raise ValueError('Algún elemento de \"lista_usuarios\" '\
																	'no es str')

		#	Directorio base de conversaciones recopiladas
		self.__conv_dir = conversation_directory

		if not self.__conv_dir.endswith('/'):
			self.__conv_dir += '/'

		self.__nombre_foro = nombre_foro 	#	Nombre del foro de recopilación
		self.__fecha_inicio = fecha_inicio 	#	Fecha de inicio de recopilación
		self.__fecha_fin = fecha_fin 		#	Fecha de fin de recopilación
		self.__doc_sol = docente_solicitante#	Docente solicitante
		self.__list_user = lista_usuarios	#	Lista completa de usuarios

		self.__active = True				#	La recopilación está activa o no

		#	Directorio auxiliar en el que se realiza la recopilación
		#	NOTA: Al tratarse de archivos destinados a enviarse desde el disco
		#	por medio del protocolo HTTP, sería conveniente codificar los
		#	caracteres no incluídos en utf-8 a la codificación admitida en las
		#	direcciones URL
		self.__comp_dir = (self.__conv_dir +
			urllib.parse.quote('recopilacion_%s_%s-%s/' % (
							self.__nombre_foro,
							self.__fecha_inicio.strftime('%d-%m-%Y_%H:%M:%S'),
							self.__fecha_fin.strftime('%d-%m-%Y_%H:%M:%S'))))

		#	Nombre de fichero a generar al acabar con la recopilación
		self.__zip_filename = (self.__conv_dir +
										(self.__comp_dir.split('/')[-2])+'.zip')

	###	Métodos privados ###

	def __install_compilation_directory(self):

		#	Crear el directorio donde se almacenará la recopilación
		os.mkdir(self.__comp_dir)

		#	Crear cada uno de los subdirectorios
		subdir_list = ['imagenes', 'documentos', 'videos', 'audios', 'notas_voz',
						'notas_video', 'stickers', 'conversaciones_recopiladas',
						'animaciones']

		for subdir in subdir_list:

			if not os.path.isdir(self.__comp_dir+subdir+'/'):
				os.mkdir(self.__comp_dir+subdir+'/')

	def __write_information_box(self):

		#	Escribir el cuadro
		self.__html_file.write(
	'''		<!-- Cuadro con información del grupo docente y la recopilación-->
	<div class="group_information" align="center">
		<h3 align="center">%s</h3>
		<div align="center">Conversaciones desde <b>%s</b> a <b>%s</b></div>
		<div align="center">Profesor solicitante: <b>%s</b></div>
		</br>
		<div align="center">Usuarios presentes en el foro:</div>

		<div>
		<ul>\n'''
		% (self.__nombre_foro,
			self.__fecha_inicio.strftime('%d/%m/%Y %H:%M:%S'),
			self.__fecha_fin.strftime('%d/%m/%Y %H:%M:%S'),
			self.__doc_sol))

		#	Escribir la lista de usuarios
		for x in self.__list_user:
			self.__html_file.write(
								'				<li>%s</li>\n' % x)

		#	Escribir el final
		self.__html_file.write(
		'''			</ul>
			</div>
		</div>
		<div class="space"></div>
		<div class="space"></div>\n''')

	def __write_color_legend(self):

		self.__html_file.write(
	'''		<!-- Cuadro con la leyenda de los colores de los mensajes-->
	<div class="space">
	<dl>
		<dt id="rectangle" style="background-color: #74C278">&ensp;&ensp;&ensp;&ensp;&ensp;</dt>
		<!-- La anchura del cuadro se rellena con espacios de texto-->
		<dd>- Mensajes enviados por alumn@s </dd>

		<dt id="rectangle" style="width:200px; background-color: #83C6E7">&ensp;&ensp;&ensp;&ensp;&ensp;</dt>
		<dd>- Mensajes enviados por el asistente</dd>

		<dt id="rectangle" style="width:200px; background-color: #FFD33E">&ensp;&ensp;&ensp;&ensp;&ensp;</dt>
		<dd>- Mensajes enviados por el profesorado</dd>

		<dt id="rectangle" style="width:200px; background-color: #C3C3C3">&ensp;&ensp;&ensp;&ensp;&ensp;</dt>
		<dd>- Mensajes no permitidos </dd>
	</dl>
	</div>
	<div class="space"></div>
	<div class="space"></div>
	<div class="space"></div>\n''')

	###	Métodos públicos ###

	def getPreviousComp(self):

		"""Permite comprobar y obtener una recopilación previa hecha con las
			mismas características que esta que se desea implementar

		Devuelve:
		--------
			str o None
			Devuelve la ruta donde se localiza la recopilación o None si no
			se ha encontrado una recopilación similar
		"""

		#	Se comprueba que no exista otra recopilación previa

		if os.path.isfile(self.__zip_filename):
			#	Existe otra recopilación y se devuelve
			return self.__zip_filename

		elif os.path.isdir(self.__comp_dir):
			t_inicio = time.time()

			#	Se está generando otra recopilación y se espera
			while os.isfile(self.__zip_filename) == False:
				#	Esperar un minuto
				time.sleep(60)

				if time.time() - t_inicio > 900:
					#	Borrar el directorio puesto que el hilo ya no funciona
					removeDirectory(self.__comp_dir)

					#	15 minutos será el máximo tiempo de espera
					return None

			return self.__zip_filename

		else:
			return None

	def start(self):

		"""Permite dar comienzo a la recopilación y preparar los directorios
			y archivos necesarios para almacenarlo
		"""

		if not self.__active:
			raise ValueError('Compilación ya terminada')

		#	Asegurar que existe el directorio base de conversaciones
		if not os.path.isdir(self.__conv_dir):
			os.mkdir(self.__conv_dir)

		if os.path.isdir(self.__comp_dir) or os.path.isfile(self.__zip_filename):
			raise ValueError('Previous recopilation is in process')

		#	Instalar los directorios donde se alamcenan la recopilación
		self.__install_compilation_directory()

		#	fichero html a crear y fichero plano en el que se escriben las
		#		las conversaciones
		self.__html_file = open(self.__comp_dir+'conversaciones.html', 'w')
		self.__plain_text_file = open((self.__comp_dir+
										'conversaciones_texto_plano.txt'), 'w')

		#	Escribir el preámbulo
		self.__html_file.write(ConversationCompiler.__HTML_PREAMBLE)

		#	Escribir el cuadro informativo
		self.__write_information_box()

		#	Escribir la leyenda de colores
		self.__write_color_legend()

	def addMensaje(self, mensajes: dict):

		"""Permite añadir un mensaje a la recopilación con toda su información

		Parámetros:
		-----------
		mensaje: OrderedDict
			Diccionario ordenado que consta del par:
			id_mensaje (int) - datos_mensaje (dict)

			Por su parte, datos_mensaje se halla compuesto por los siguientes
			parámetros:
			- nombre_usuario: str
				Nombre del usuario que envió el mensaje

			- tipo_usuario: str
				Indica el tipo de usuario que envió el mensaje: docente y alumno
				None si el mensaje es del asistente

			- fecha: datetime.datetime
				Fecha en la que se envió o reibió el mensaje

			- academico: bool
				Indica si el mensaje es académico o no. Sólo tiene sentido
				para los mensajes recibidos en foros docentes

			- tipo_evento: str
				Tipo del evento acontecido en el chat grupal

			Para los mensajes, se incluyen los campos nombre_usuario,
				tipo_usuario, fecha y academico, mientras que para los Eventos
				se incluyen los campos nombre_usuario, tipo_usuario, fecha y
				tipo_evento

			- datos: dict
				Almacena los datos que incluye el mensaje

			En concreto, datos puede presentar los siguientes formatos

			Para tipo texto:

			·tipo_dato: 'texto'
			·texto: str o list str
			 	Texto o textos a almacenar

			Para tipo Multimedia con Archivo:

			·tipo_dato: str
				Tipo de Dato Multimedia almacenado: Puede adoptar los valores
				'imagen', 'audio', 'video'. 'nota_voz', 'nota_video',
				'documento','animacion' y 'sticker'

			·ruta_archivo: str o None
				Ruta en el sistema de ficheros en la que el servidor ha
				almacenado el Archivo.

			·mime type: str o None
				Valor del encabezado Mime asociado al archivo

			·file id: int o None
				Identificador de archivo asociado por la plataforma de
				mensajerı́a a dicho Archivo.

			·sticker_emoji: str o None
				emoji asociado al Sticker. Sólo para stickers
				Parámetro opcional

			·sticker_conjunto: str o None
				Nombre del conjunto al que pertenece el Sticker.
				Sólo para stickers
				Parámetro opcional

			·sticker_tipo: str o None
				Tipo de sticker, puede adoptar dos valores: normal o animado.
				Sólo para stickers.
				Parámetro opcional
				NOTA: Actualmente en desuso

			Para tipo Contacto:

			·tipo_dato: 'contacto'

			·nombre: str
				Nombre o primer nombre asociado al Contacto.

			·apellidos: str o None
				Nombre o segundo nombre asociado al Contacto.
				Parámetro opcional

			·telefono: int
				Número de teléfono asociado al Contacto.

			·vcard: str o None
				Datos recogidos en la vcard asociada al Contacto.
				Parámetro opcional

			·id_usuario: int o None
				Identificador de usuario asociado por la plataforma de
				mensajerı́a al usuario asociado al Contacto.
				Parámetro opcional

			Para tipo Localizacion y Avenida:

			·tipo_dato: 'localizacion'

			·latitud: int
				Latitud geográfica de la Localizacion o Avenida.

			·longitud: int
				Longitud geográfica de la Localizacion o Avenida

			·titulo: str o None
				Tı́tulo que recibe la Avenida localizada en la Localizacion.
				Parámetro opcional

			·direccion: str o None
				Direccion de la avenida localizada en la Localizacion.
				Parámetro opcional

			·id cuadrante: int o None
				Identificador del cuadrante asociado a la avenida localizada en
				la Localizacion. Parámetro opcional

			·tipo cuadrante: str o None
				Tipo de cuadrante asociado a la avenida localizada en la
				Localizacion.
				Parámetro opcional

		"""

		if self.__active == False:
			raise ValueError('Compilación ya terminada')

		if not mensajes:
			return

		#	Se añade cada mensaje a la web
		for m in mensajes:

			#	Añadir cuadro de eventos
			if 'evento' in mensajes[m]:
				self.__html_file.write('\t\t<div class="parent_evento_box">\n')
				self.__html_file.write(
					('\t\t\n<div class="evento_box"><b>%s</b></div>\n' %
														mensajes[m]['evento']))
				self.__html_file.write('\t\t</div>\n')

				self.__plain_text_file.write('%s - %s\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['evento']))

				#	Añadir cierre
				self.__html_file.write('\t\t</div>\n<div class="space"></div>\n')
				continue


			for c in mensajes[m]['datos']:

				#	Añadir cualquier otra cosa
				#	Añadir div contenedor adecuado
				if mensajes[m]['tipo_usuario'] == 'docente':
					self.__html_file.write(
									'\t\t<div class="message_box_professor">\n')
				elif not mensajes[m]['tipo_usuario']:
					self.__html_file.write(
							'\t\t<div class="message_box_bot" align="right">\n')
				elif mensajes[m]['academico']:
					self.__html_file.write('\t\t<div class="message_box">\n')
				else:
					self.__html_file.write('\t\t<div class="message_box_ban">\n')

				#	Añadir usuario emisor
				self.__html_file.write(('\t\t\t<div class="name">%s</div>\n' %
												mensajes[m]['nombre_usuario']))

				#	Añadir contenido
				if mensajes[m]['datos'][c]['tipo_dato'] == 'texto':
					self.__html_file.write(
							('\t\t\t<div class="content">%s</div>\n' %
										mensajes[m]['datos'][c]['contenido']))

					#	Añadir dato al fichero texto plano
					self.__plain_text_file.write('%s - %s %s - %s%s\n' % (
			mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
			mensajes[m]['nombre_usuario'],
			'[DOCENTE]' if mensajes[m]['tipo_usuario'] == 'docente' else '',
			mensajes[m]['datos'][c]['contenido'],
			' - mensaje no permitido' if not mensajes[m]['academico'] else ''))

				elif mensajes[m]['datos'][c]['tipo_dato'] == 'imagen':

					if (not mensajes[m]['datos'][c]['contenido'] or
					not os.path.isfile(mensajes[m]['datos'][c]['contenido'])):
						#	Si la imagen no se encuentra almacenada no se adjunta
						self.__html_file.write('\t\t\t<div>Imagen</div>')

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
										'%s - %s - Imagen no encontrada\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'])
						)

					else:
						new_file = copyFile(mensajes[m]['datos'][c]['contenido'],
									self.__comp_dir+'imagenes/')

						#	Establecer la ruta de forma relativa
						new_file = './'+'/'.join( new_file.split('/')[-2:] )

						#	Añadir la imagen
						self.__html_file.write(
									'\t\t\t<img src="%s" alt="%s">' % (new_file,
									'Imagen de %s' % mensajes[m]['nombre_usuario']
									))

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write('%s - %s - Imagen: %s\n'% (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'],
							new_file)
							)

				elif mensajes[m]['datos'][c]['tipo_dato'] in ('video',
																'nota_video'):

					if (not mensajes[m]['datos'][c]['contenido'] or
					not os.path.isfile(mensajes[m]['datos'][c]['contenido'])):
						#	Si el vídeo no se encuentra almacenada no se adjunta
						self.__html_file.write('\t\t\t<div>Video</div>')

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Vídeo no encontrado\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'])
							)

					else:
						new_file = copyFile(
										mensajes[m]['datos'][c]['contenido'],
										self.__comp_dir+'videos/')

						mimetype = mensajes[m]['datos'][c]['mime_type']

						#	Establecer la ruta de forma relativa
						new_file = './'+'/'.join( new_file.split('/')[-2:] )

						#	Añadir el vídeo
						self.__html_file.write(
'\t\t\t<video controls>\n\t\t\t\t<source src="%s" type="%s">\n\t\t\t</video>\n' % (new_file, mimetype))

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Vídeo: %s\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'],
							new_file)
						)

				elif mensajes[m]['datos'][c]['tipo_dato'] in ('audio',
																'nota_voz'):

					if (not mensajes[m]['datos'][c]['contenido'] or
					not os.path.isfile(mensajes[m]['datos'][c]['contenido'])):
						#	Si el audio no se encuentra almacenada no se adjunta
						self.__html_file.write('\t\t\t<div>Audio</div>')

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Audio no encontrado\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'])
						)

					else:
						new_file = copyFile(mensajes[m]['datos'][c]['contenido'],
									self.__comp_dir+'audios/')

						mimetype = mensajes[m]['datos'][c]['mime_type']

						#	Establecer la ruta de forma relativa
						new_file = './'+'/'.join( new_file.split('/')[-2:] )

						#	Añadir el audio
						self.__html_file.write(
		'\t\t\t<audio>\n\t\t\t\t<source src="%s" type="%s">\n\t\t\t</audio>\n'
												% (new_file, mimetype))

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Audio: %s\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'],
							new_file)
						)

				elif mensajes[m]['datos'][c]['tipo_dato'] == 'contacto':
					#	Añadir el contacto a html
					self.__html_file.write('\t\t\t<div class="contacto_box">\n')
					self.__html_file.write('\t\t\t\t<div><b>Contacto</b></div>\n')
					self.__html_file.write('\t\t\t\t<div><ul style="disc">\n')
					self.__html_file.write(
						('\t\t\t\t\t<li><b>Teléfono:</b>%s</li>\n' %
										mensajes[m]['datos'][c]['telefono']))
					self.__html_file.write(
						('\t\t\t\t\t<li><b>Nombre:</b>%s</li>\n' %
											mensajes[m]['datos'][c]['nombre']))

					if ('apellidos' in mensajes[m]['datos'][c] and
										mensajes[m]['datos'][c]['apellidos']):
						self.__html_file.write(
							('\t\t\t\t\t<li><b>Apellidos:</b>%s</li>\n' %
									mensajes[m]['datos'][c]['apellidos']))

					if ('vcard' in mensajes[m]['datos'][c] and
										mensajes[m]['datos'][c]['vcard']):
						self.__html_file.write(
						('\t\t\t\t\t<li><b>Información de VCard:</b>%s</li>\n' %
						mensajes[m]['datos'][c]['vcard']))

					self.__html_file.write('\t\t\t\t</ul></div>\n')
					self.__html_file.write('\t\t\t</div>\n')

					#	Añadir dato al fichero texto plano

					#	Obtener copia del diccionario donde no aparezca el
					#	campo tipo_dato para incluir en el fichero plano
					dict_aux = dict(mensajes[m]['datos'][c])
					dict_aux.pop('tipo_dato')

					self.__plain_text_file.write(
							'%s - %s - Contacto: %s\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'],
							dict_aux)
							)

				elif mensajes[m]['datos'][c]['tipo_dato'] == 'localizacion':

					#	Añadir el contacto a html
					self.__html_file.write('\t\t\t<div class="contacto_box">\n')
					if ('titulo' in mensajes[m]['datos'][c] and
											mensajes[m]['datos'][c]['titulo']):
						self.__html_file.write(
										'\t\t\t\t<div><b>Avenida</b></div>\n')
					else:
						self.__html_file.write(
									'\t\t\t\t<div><b>Localización</b></div>\n')

					self.__html_file.write('\t\t\t\t<div><ul style="disc">\n')
					self.__html_file.write(
									('\t\t\t\t\t<li><b>Longitud:</b>%f</li>\n' %
										mensajes[m]['datos'][c]['longitud']))
					self.__html_file.write(
									('\t\t\t\t\t<li><b>Latitud:</b>%s</li>\n' %
									mensajes[m]['datos'][c]['latitud']))

					if ('titulo' in mensajes[m]['datos'][c] and
											mensajes[m]['datos'][c]['titulo']):
						self.__html_file.write(
						('\t\t\t\t\t<li><b>Titulo de la avenida:</b>%s</li>\n' %
											mensajes[m]['datos'][c]['titulo']))
						self.__html_file.write(
							('\t\t\t\t\t<li><b>Tipo de Avenida:</b>%s</li>\n' %
							mensajes[m]['datos'][c]['tipo_cuadrante']))
					self.__html_file.write('\t\t\t\t</ul></div>\n')
					self.__html_file.write('\t\t\t</div>\n')

					#	Añadir dato al fichero texto plano

					#	Obtener copia del diccionario donde no aparezca el
					#	campo tipo_dato para incluir en el fichero plano
					dict_aux = dict(mensajes[m]['datos'][c])
					dict_aux.pop('tipo_dato')

					self.__plain_text_file.write(
							'%s - %s - Localización: %s\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'],
							dict_aux)
							)

				elif mensajes[m]['datos'][c]['tipo_dato'] == 'sticker':

					#	Añadir el sticker
					if (not mensajes[m]['datos'][c]['contenido'] or
					not os.path.isfile(mensajes[m]['datos'][c]['contenido'])):
						self.__html_file.write('\t\t\tSticker no encontrado\n')

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Sticker no encontrado\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'])
							)
					else:
						new_file = copyFile(mensajes[m]['datos'][c]['contenido'],
									self.__comp_dir+'stickers/')

						#	Establecer la ruta de forma relativa
						new_file = './'+'/'.join( new_file.split('/')[-2:] )

						self.__html_file.write(
						'\t\t\t<img class="transparent" src="%s" alt="%s">\n'% (
											new_file, 'Sticker: %s' % new_file))

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Sticker: %s\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'],
							new_file)
						)

				elif mensajes[m]['datos'][c]['tipo_dato'] == 'animacion':

					#	Añadir la animación
					if (not mensajes[m]['datos'][c]['contenido'] or
					not os.path.isfile(mensajes[m]['datos'][c]['contenido'])):
						self.__html_file.write('\t\t\tAnimación no encontrada\n')

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Animación no encontrada\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'])
						)
					else:
						new_file = copyFile(mensajes[m]['datos'][c]['contenido'],
									self.__comp_dir+'animaciones/')

						#	Establecer la ruta de forma relativa
						new_file = './'+'/'.join( new_file.split('/')[-2:] )

						#	Determinar si es un gif o vídeo e insertarla
						tipo = mensajes[m]['datos'][c]['mime_type'].split('/')[0]

						mimetype = mensajes[m]['datos'][c]['mime_type']

						if tipo == 'image':
							self.__html_file.write(
							'\t\t\t<img src="%s" alt="%s">\n' % (
							new_file,
							'Animación de: %s' % mensajes[m]['nombre_usuario']))
						elif tipo == 'video':
							self.__html_file.write('\t\t\t<video controls>\n\t\t\t\t<source src="%s" type="%s">\n\t\t\t</video>\n' % (new_file, mimetype))

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Animación: %s\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'],
							new_file)
						)

				else:

					if (not mensajes[m]['datos'][c]['contenido'] or
					not os.path.isfile(mensajes[m]['datos'][c]['contenido'])):
						#	Si el documento no se encuentra almacenada
						#	no se adjunta
						self.__html_file.write(
									'\t\t\t<div>Documento no encontrado</div>')

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
							'%s - %s - Documento no encontrado\n' % (
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
							mensajes[m]['nombre_usuario'])
						)

					else:
						new_file = copyFile(mensajes[m]['datos'][c]['contenido'],
									self.__comp_dir+'documentos/')

						#	Establecer la ruta de forma relativa
						new_file = './'+'/'.join( new_file.split('/')[-2:] )

						#	Añadir el audio
						self.__html_file.write('\t\t\t<div align="center"><a class="documento_button" href="%s">&#x1F4C4 Documento</a></div>\n'
												% (new_file))

						#	Añadir dato al fichero texto plano
						self.__plain_text_file.write(
								'%s - %s - Documento: %s\n' % (
								mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M:%S'),
								mensajes[m]['nombre_usuario'],
								new_file)
							)

				#	Añadir fecha
				self.__html_file.write(
						('\t\t\t<div class="date" align="right">%s</div>' %
							mensajes[m]['fecha'].strftime('%d/%m/%Y %H:%M')))

				#	Añadir cierre
				self.__html_file.write('\t\t</div>\n<div class="space"></div>\n')


	def close(self):

		"""Permite dar por finalizada la compilación

		Devuelve:
			str: Ruta al fichero comprimido con los resultados de la compilación
		"""

		#	Cerrar el documento html
		self.__html_file.write('\t</body>\n</html>')

		self.__html_file.close()
		self.__plain_text_file.close()

		#	Comprimir el contenido del directorio en un zip
		f = zipfile.ZipFile(self.__zip_filename, mode='w')

		for x in os.listdir(self.__comp_dir):
			filename = self.__comp_dir+x
			relative_filename = os.path.basename(self.__comp_dir)+x

			if os.path.isfile(filename):
				#	Agregar cada archivo del directorio
				f.write(filename, relative_filename)
			elif os.path.isdir(filename):
				#	Introducir los archivos del subdirectorio
				#	(sólo se espera un nivel de anidación)
				for y in os.listdir(filename):
					f.write(filename+'/'+y, filename.split('/')[-1]+'/'+y)

		f.close()

		#	Borrar el directorio
		removeDirectory(self.__comp_dir)

		self.__active = False

		return self.__zip_filename

	def __del__(self):
		if self.__active:
			self.close()
