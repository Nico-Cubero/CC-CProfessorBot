# -*- coding: utf-8 -*-
################################################################################
# Descripción: Módulo que contiene la definición e implementación de la
#				clase BotServer
# Autor: Nicolás Cubero Torres
################################################################################

### Módulos importados ###
import logging
import json
import os
import os.path
import sys
import time
import re
import datetime
import mimetypes
import urllib
from collections import OrderedDict
import telegram
import telegram.ext
from telegram.ext import (ConversationHandler, CommandHandler, MessageHandler,
						RegexHandler, CallbackQueryHandler, InlineQueryHandler)
from telegram.ext import Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from cprofessorbot.botServerDAO import BotServerDAO
from cprofessorbot.questionManager import QuestionManager
from cprofessorbot.utils import EnteringGroupHandler
from cprofessorbot.utils import MemberEnteringGroupHandler
from cprofessorbot.utils import MemberLefteringGroupHandler
from cprofessorbot.utils import LefteringGroupHandler
from cprofessorbot.utils import ConversationCompiler
from cprofessorbot.utils import emojis
from cprofessorbot.utils import copyFile
from cprofessorbot.nlu import (SpeechHandler, parseSpeechDate, parseSpeechTime,
														replaceSpeechNumber)

class BotServer:

	"""
	Sistema servidor del bot C-ProfessorBot que se ocupa del funcionamiento
	completo del Bot conversacional

	Parámetros:
	-----------
	config_filename: str
		Ruta del archivo JSON que contiene el archivo de configuración tomado
		por el sistema y que incluye los valores de los parámetros requeridos
		para su funcionamiento.

	debug_mode: bool (default False)
		Permite establecer el modo de depuración del sistema (True) o no (False)

	Nota
	------
	El archivo "config_file" de configuración debe de recibir los siguientes
	parámetros:
	- bot_token: string
		Token del bot Telegram por el que se comunicará el sistema
	- directorio_base: string
		Ruta del directorio donde el bot almacenará y gestionará todos los
		archivos requeridos para su funcionamiento
	- usuario_docente_password: string
		Contraseña que se se desea establecer como contraseña de registro
		a los usuarios docentes
	- fuentes_conceptos: string o lista(string)
		Ruta de archivos o URLs con las preguntas teóricas que el sistema
		descargará y almacenará en sus base de datos
	- umbral_eval_conv: float
		Umbral de puntuación de pertenenecia al ámbito académico mínimo
		requerido para que un mensaje recibido en un grupo o supergrupo sea
		considerado como perteneciente al ámbito académico
	- avisos_ban: integer
		Número de avisos requeridos para efectuar el baneo de un usuario
	"""

	def __init__(self, config_filename: str, debug_mode: bool=False):

		"""
		Parámetros:
		--------------

		token : str
			Tóken del bot Telegram que se comunicará y será gestionado por este
			servidor
		"""

		#	Atributos privados
		self.__config = None			# Configuración del sistema
		self.__token = None				# Tóken del bot Telegram
		self.__bd_interface	= None		# Interfaz de acceso a la base de datos
		self.__quest_manager = None		# Administrador de preguntas teóricas
		self.__speech_handler = None	# Evaluador del tema de la conversación
		self.__bot_interface = None		# Interfaz del bot
		self.__bot_updater = None		# Actualizador de la interfaz
		self.__debug_mode = debug_mode	# Modo de depuración

		#	Configurar el logging del sistema
		self.__log = logging.getLogger('cprofessorbot_log')
		logging.basicConfig(format='%(levelname)s - %(asctime)s - %(message)s',
							datefmt='%d-%b-%y %H:%M:%S')

		self.__log.setLevel(logging.getLevelName(
									'DEBUG' if self.__debug_mode else 'INFO'))

		#	Cargar el fichero de configuración y comprobar que es correcto
		with open(config_filename,'r') as config_file:
			try:
				self.__config = json.load(config_file)
			except json.decoder.JSONDecodeError:
				raise ValueError('El fichero de configuración presenta '\
											'errores o caracteres no válidos')
				exit(1)
			except:
				raise ValueError('El fichero de configuración no se encuentra')
				exit(1)

		self.__check_config_file()

		self.__token = self.__config['bot_token']


	### Atributos estáticos privados ###

	#	Constantes para almacenar todas las opciones del menú
	__OPCIONES_MENU_PRINCIPAL = [
		[KeyboardButton(u'Gestionar grupos docentes %s%s' % (emojis.PROFESOR,
															emojis.PROFESORA))],
		[KeyboardButton(u'Comunicados %s' % emojis.MEGAFONO)],
		[KeyboardButton((u'Descargar conversaciones del alumnado %s' %
														emojis.MEMORIA_PAPEL))],
		[KeyboardButton(u'Dar de baja como profesor/ra %s' % emojis.BOMBA)],
		[KeyboardButton(u'Salir %s' % emojis.MANO_ADIOS)]
	]

	(__MOSTRAR_MENU, __SELECT_OP_MENU_PRINCIPAL, __SELECT_OP_GEST_DOCENTE,
	__SELECT_OP_GEST_ALUMNOS, __SELECT_OP_ELIM_GRUPO,
	__SELECT_OP_ELIM_GRUPO_CONF, __SELECT_OP_BAN_ALUMNO,
	__SELECT_OP_READMITIR_ALUMNO, __SELECT_OP_ELIM_ALUMNO,
	__SELECT_OP_ELIM_ALUMNO_CONF, __DESC_CONVERS_CONF_FECHA_INICIO,
	__DESC_CONVERS_CONF_HORA_INICIO, __DESC_CONVERS_CONF_FECHA_FIN,
	__DESC_CONVERS_CONF_HORA_FIN, __DESC_CONVERS_SELECT_GRUPO,
	__DESC_CONVERS_CONF_GRUPO, __SELECT_OP_BAJA, __SELECT_OP_BAJA_CONF,
	__SELECT_OP_GEST_COMUNICADO, __SELECT_OP_ELIM_COMUNICADO,
	_PROG_COMUNICADO_CONF_FECHA, __PROG_COMUNICADO_CONF_HORA,
	__PROG_COMUNICADO_SELECT_GRUPO, __PROG_COMUNICADO_ANCLAR,
	__PROG_COMUNICADO_CONTENIDO) = range(25)

	#	Plantilla del fichero de configuración
	__CONFIG_FILE_TEMP = {
							'directorio_base':'.',
							'bot_token':'',
							'usuario_docente_password':'',
							'fuentes_conceptos': [],
							'umbral_eval_conv': 0.6,
							'avisos_ban': 3
						}

	#	Tamaño de las particiones en las que se dividirán los mensajes
	#	a recopilar para las descarga de conversaciones
	__DESC_CONV_PART = 10000

	#	Números de minutos a esperar antes de comprobar si los datos
	#	de un chat grupal que constituye el foro docente han sido actualizados
	#	y actualizar la información que se tiene de él en la bd
	__MIN_ACT = 5

	### Métodos privados ###
	def __initialize_interface(self):

		"""
		Inicializa la interfaz que comunica con el bot Telegram, así como su
			actualizador y despachador de eventos

		"""

		#	Crear la interfaz, el actualizador y despachador de eventos
		interface = telegram.Bot(token=self.__token)
		updater = telegram.ext.Updater(token=self.__token)
		dispatcher = updater.dispatcher

		###	Declaración de todos los manejadores ###

		#	Manejador del comando /start en chats privados
		start_command_private_handler = telegram.ext.CommandHandler(
									'start',
									self.__start_command_private_callback,
									filters=~Filters.group,
									pass_user_data=True)

		#	Manejador del comando /start en chats públicos
		start_command_group_handler = telegram.ext.CommandHandler(
									'start',
									self.__start_command_group_callback,
									filters=Filters.group,
									pass_chat_data=True)

		#	Manejador de las expresiones de saludo efectuadas por los usuarios
		#	al sistema en chats privados
		saludo_handler = telegram.ext.MessageHandler(
							(Filters.text &
							 Filters.regex(
									'(?i)^(hol[^ ]|hey|buen[ao]s|saludos).*') &
							 (~Filters.group)),
							self.__saludo_callback,
							pass_user_data=True)

		#	Manejador del comando \ask en chats privados
		ask_private_command_handler = CommandHandler('ask',
										self.__ask_question_private_callback,
										filters=(~Filters.group),
										pass_user_data=True)

		#	Manejador del comando \ask en chats públicos
		ask_group_command_handler = CommandHandler('ask',
										self.__ask_question_group_callback,
										filters=Filters.group,
										pass_chat_data=True)

		#	Manejador de las expresiones de consultas teóricas efectuadas
		#	por los usuarios al bot en chats privados
		ask_speech_private_handler = MessageHandler(
					(Filters.regex('^(?i)(profe(s{1,2}or)?),?( )*(.*)') &
					(~Filters.group)),
					self.__ask_question_private_callback,
					pass_user_data=True)

		#	Manejador de las expresiones de consultas teóricas efectuadas
		#	por los usuarios al bot en chats públicos
		ask_speech_group_handler = MessageHandler(
					(Filters.regex('^(?i)(profe(s{1,2}or)?),?( )*(.*)') &
					Filters.group),
					self.__ask_question_group_callback,
					pass_chat_data=True)

		#	Manejador del mensaje con la clave de registro de usuario docente
		enter_registry_key_handler = MessageHandler(
			(Filters.regex(self.__config['usuario_docente_password']) &
			(~Filters.group)),
		 	self.__registro_usuario_docente,
			pass_user_data=True)

		#	Manejador del menú principal docente
		conv_menu_handler = ConversationHandler(
			entry_points=[start_command_private_handler,
							saludo_handler,
						  enter_registry_key_handler],
			states={
				BotServer.__SELECT_OP_MENU_PRINCIPAL: [
						RegexHandler((u'Gestionar grupos docentes %s%s' %
										(emojis.PROFESOR, emojis.PROFESORA)),
										self.__gestion_grupo_docente_callback,
										pass_user_data=True),

						RegexHandler('Programar Comunicado al alumnado',
									self.__programar_comunicado_callback,
									pass_user_data=True),

						RegexHandler(u'Comunicados %s' % emojis.MEGAFONO,
									self.__gestion_comunicados_callback,
									pass_user_data=True),

						RegexHandler((u'Descargar conversaciones del alumnado %s'
										% emojis.MEMORIA_PAPEL),
									self.__descargar_conversaciones_callback,
									pass_user_data=True),

						RegexHandler((u'Dar de baja como profesor/ra %s' %
										emojis.BOMBA),
									self.__baja__callback,
									pass_user_data=True),

						RegexHandler(u'Salir %s' % emojis.MANO_ADIOS,
									self.__salir_menu,
									pass_user_data=True),
					],

				BotServer.__SELECT_OP_GEST_DOCENTE: [
						CallbackQueryHandler(
									self.__select_op_gest_docente_callback,
									pass_user_data=True)
						],

				BotServer.__SELECT_OP_ELIM_GRUPO: [
						CallbackQueryHandler(
							self.__select_op_elim_grupo_callback,
							pass_user_data=True)
						],

				BotServer.__SELECT_OP_ELIM_GRUPO_CONF: [
						CallbackQueryHandler(
							self.__select_op_elim_grupo_conf_callback,
							pass_user_data=True)
						],
				BotServer.__SELECT_OP_GEST_ALUMNOS: [
						CallbackQueryHandler(
							self.__select_op_gest_alumnos_callback,
							pass_user_data=True)
						],
				BotServer.__SELECT_OP_BAN_ALUMNO: [
						CallbackQueryHandler(
							self.__select_op_ban_alumno_callback,
							pass_user_data=True)
						],
				BotServer.__SELECT_OP_READMITIR_ALUMNO: [
						CallbackQueryHandler(
							self.__select_op_readmitir_alumno_callback,
							pass_user_data=True)
						],
				BotServer.__SELECT_OP_ELIM_ALUMNO: [
						CallbackQueryHandler(
							self.__select_op_elim_alumno_callback,
							pass_user_data=True)
						],
				BotServer.__SELECT_OP_ELIM_ALUMNO_CONF: [
						CallbackQueryHandler(
							self.__select_op_elim_alumno_conf_callback,
							pass_user_data=True)
						],
				BotServer._PROG_COMUNICADO_CONF_FECHA: [
						MessageHandler(Filters.text,
							self.__comunicado_fecha_conf_callback,
							pass_user_data=True)
						],
				BotServer.__PROG_COMUNICADO_CONF_HORA: [
						MessageHandler(Filters.text,
							self.__comunicado_hora_conf_callback,
							pass_user_data=True)
						],
				BotServer.__PROG_COMUNICADO_SELECT_GRUPO: [
						CallbackQueryHandler(
							self.__comunicado_select_grupo_callback,
							pass_user_data=True)
						],

				BotServer.__PROG_COMUNICADO_CONTENIDO: [
						CallbackQueryHandler(self.__comunicado_conf_contenido,
												pass_user_data=True),
						MessageHandler(Filters.all,
										self.__comunicado_contenido_callback,
										pass_user_data=True,edited_updates=True)
						],
				BotServer.__SELECT_OP_GEST_COMUNICADO: [
						CallbackQueryHandler(
							self.__select_op_gest_comunicado_callback,
							pass_user_data=True)
						],
				BotServer.__SELECT_OP_ELIM_COMUNICADO: [
						CallbackQueryHandler(
							self.__select_op_elim_comunicado_callback,
							pass_user_data=True)
						],
				BotServer.__DESC_CONVERS_CONF_FECHA_INICIO: [
						MessageHandler(Filters.text,
							self.__desc_convers_conf_fecha_inicio_callback,
							pass_user_data=True)
						],
				BotServer.__DESC_CONVERS_CONF_HORA_INICIO: [
						MessageHandler(Filters.text,
							self.__desc_convers_conf_hora_inicio_callback,
							pass_user_data=True)
						],
				BotServer.__DESC_CONVERS_CONF_FECHA_FIN: [
						MessageHandler(Filters.text,
							self.__desc_convers_conf_fecha_fin_callback,
							pass_user_data=True)
						],
				BotServer.__DESC_CONVERS_CONF_HORA_FIN: [
						MessageHandler(Filters.text,
							self.__desc_convers_conf_hora_fin_callback,
							pass_user_data=True)
						],
				BotServer.__DESC_CONVERS_SELECT_GRUPO: [
						CallbackQueryHandler(
							self.__desc_convers_select_grupo_callback,
							pass_user_data=True)
						],
				BotServer.__DESC_CONVERS_CONF_GRUPO: [
						CallbackQueryHandler(
							self.__desc_convers_conf_grupo_callback,
							pass_user_data=True)
						],
				BotServer.__SELECT_OP_BAJA: [
						CallbackQueryHandler(self.__select_op_baja_callback,
												pass_user_data=True)
						],
				BotServer.__SELECT_OP_BAJA_CONF: [
						CallbackQueryHandler(
							self.__select_op_baja_conf_callback,
							pass_user_data=True)
						]

			},
			fallbacks=[MessageHandler(Filters.text,
												self.__menu_fallback_callback)],
			conversation_timeout=datetime.timedelta(minutes=20)
		)

		# Manejador del evento de entrada del sistema a un grupo
		entering_group_handler = EnteringGroupHandler(
									self.__entrada_grupo_callback,
									pass_chat_data=True)

		exiting_group_handler = LefteringGroupHandler(
									self.__exit_group_callback,
									pass_chat_data=True)

		#	Manejador de los eventos producidos cuando un usuario se agrega
		#	a un grupo existente
		enter_member_group_handler = MemberEnteringGroupHandler(
										self.__enter_member_group_callback,
										pass_chat_data=True)

		#	Manejador de los eventos producidos cuando un usuario sale
		#	a un grupo existente
		exit_member_group_handler = MemberLefteringGroupHandler(
										self.__exit_member_group_callback,
										pass_chat_data = True
									)

		# Manejador de mensajes de chats privados
		messages_private_handler = MessageHandler(
							(~Filters.group),
							self.__message_private_callback,
							pass_user_data=True)

		# Manejador de mensajes de chats públicos
		messages_group_handler = MessageHandler(
							Filters.group & (~Filters.status_update),
							self.__message_group_callback,
							pass_chat_data=True,
							edited_updates=True)


		#	Añadir los manejadores al despachador de eventos
		dispatcher.add_handler(entering_group_handler)
		dispatcher.add_handler(exiting_group_handler)
		dispatcher.add_handler(enter_member_group_handler)
		dispatcher.add_handler(exit_member_group_handler)
		dispatcher.add_handler(start_command_group_handler)
		dispatcher.add_handler(ask_private_command_handler)
		dispatcher.add_handler(ask_group_command_handler)
		dispatcher.add_handler(ask_speech_private_handler)
		dispatcher.add_handler(ask_speech_group_handler)
		dispatcher.add_handler(messages_group_handler)
		dispatcher.add_handler(conv_menu_handler)
		dispatcher.add_handler(messages_private_handler)
		dispatcher.add_error_handler(self.__error_handler)

		return interface, updater

	def __check_config_file(self):

		"""Función encargada de comprobar que un diccionario/documento JSON
		pasado como fichero de configuración, presente todos los campos
		requeridos y con el tipo de datos y valores correctos
		"""

		#	Se comprueba que no falte ningún campo
		if len(self.__config) != len(BotServer.__CONFIG_FILE_TEMP):
			raise ValueError('Los campos proporcionados en el fichero de'\
								' configuración no son válidos')

		#	Se comprueba que los campos son válidos
		for campo in self.__config.keys():

			if campo not in BotServer.__CONFIG_FILE_TEMP:
				raise ValueError('Campo "%s" no admitido' % campo)

			if campo  == 'fuentes_conceptos' and not isinstance(
											self.__config[campo], (str, list)):
					raise ValueError('El valor del campo "%s" no es una cadena'\
										' de caracteres válida o lista'\
										'de cadenas de caracteres' % campo)

			elif isinstance(BotServer.__CONFIG_FILE_TEMP[campo], str):

				if not isinstance(self.__config[campo], str):
					raise ValueError('El valor del campo "%s" no es una cadena'\
										' de caracteres válida' % campo)

				elif not self.__config[campo]:
					raise ValueError('El campo "%s" está vacío' % campo)

			elif type(BotServer.__CONFIG_FILE_TEMP[campo]) is float:

				if type(self.__config[campo]) not in (int, float):
					raise ValueError('El valor del campo "%s" no es un número'\
										' válido' % campo)

			elif type(BotServer.__CONFIG_FILE_TEMP[campo]) is int:

				if type(self.__config[campo]) is not int:
					raise ValueError('El valor del campo "%s" no es un'\
										' número válido' % campo)

		#	Revisar que el campo "umbral_eval_conv" tenga un valor válido
		if (self.__config['umbral_eval_conv'] < 0.0 or
				self.__config['umbral_eval_conv'] > 1.0):
			raise ValueError('El campo "umbral_eval_conv" del fichero de'\
								' configuración debe tener un valor'\
								' comprendido entre 0 y 1')

		if self.__config['avisos_ban'] < 1:
			raise ValueError('El campo "avisos_ban" del fichero de'\
								' configuración debe ser mayor o igual que 1')

		#	Arreglar la ruta del directorio base
		if not self.__config['directorio_base'].endswith('/'):
			self.__config['directorio_base'] += '/'

	def __ask_question_private_callback(self, bot, update, user_data):

		"""Función manejadora de las preguntas efectuadas por los usuarios
		en un chat  privado
		"""

		mensaje = update.message.text.lower() #	Tomar el mensaje en minúscula

		id_chat_emisor = update.effective_chat.id
		usuario = update.effective_user.first_name
		id_usuario = update.effective_user.id
		id_mensaje = update.message.message_id

		pregunta = None

		###	Para mensajes privados ###

		#	Tomar los datos del usuario, buscarlos si es necesario
		#	e introducirlos en contexto
		if 'usuario' not in user_data:
			user_data['usuario'] = self.__bd_interface.getUsuario(id_usuario)

		#	El usuario es ignorado si no está registrado
		if not user_data['usuario'] or not user_data['usuario']['valido']:

			#	Borra los datos de contexto y salir
			user_data.clear()
			return

		#	Tratar de tomar la pregunta si se ha usado un comando
		m = re.search('/ask( )*(.*)', mensaje)

		if m:
			pregunta = m.group(2)
		else:
			#	Tomar la pregunta si se llama al profesor
			m = re.search(('^(profe(s{1,2}or)?|@%s),?( )*(.*)' %
											bot.get_me().username),mensaje)

			if m:
				pregunta = m.group(4)

		#	Se considera el texto entero como pregunta si no empareja
		#	con ninguna expresión
		if not pregunta:
			pregunta = mensaje

		bot_men = bot.sendMessage(chat_id=update.message.chat_id,
									text='Un momento %s' % usuario)
		self.__registrar_mensaje(mensaje=bot_men, recibido=False)

		#	Programar una tarea encargada de buscar y enviar la respuesta
		self.__bot_updater.job_queue.run_once(
								callback=self.__answer_question_callback,
								when=0,
								context={
											'id_chat': id_chat_emisor,
											'usuario': usuario,
											'id_mens_resp': id_mensaje,
											'pregunta': pregunta
									}
								)

	def __ask_question_group_callback(self, bot, update, chat_data):

		"""Función manejadora de las preguntas efectuadas por los usuarios
		en un chat público
		"""

		mensaje = update.message.text.lower() #	Tomar el mensaje en minúscula

		id_chat_emisor = update.effective_chat.id
		usuario = update.effective_user.first_name
		id_usuario = update.effective_user.id
		id_mensaje = update.message.message_id

		pregunta = None
		academico = True

		###	Para mensajes grupales ###

		#	Tomar los datos del foro e introducirlos en contexto
		#	Cargar los datos del grupo y de sus participantes,
		self.__load_datos_grupo_callback(bot, update, chat_data)

		#	Registrar el foro si no estaba registrado
		self.__registro_foro_handler(bot, update, chat_data)


		#	Registrar al ususario que envía el mensaje si no estaba
		#	registrado
		self.__registrar_usuario_grupo_handler(bot, update.effective_user,
												update.effective_chat,
												chat_data)

		#	Registrar cada uno de los usuarios que pudieran haberse unido al
		#	grupo en este momento
		mensaje_dato = update.message or update.edited_message
		for usuario in mensaje_dato.new_chat_members:
			self.__registrar_usuario_grupo_handler(bot, usuario,
													update.effective_chat,
													chat_data)

		#	Realizar actualizaciones de los datos del grupo si hubiera
		#	pasado el tiempo mínimo requerido
		t_time = (datetime.datetime.now() -
		chat_data['foros'][update.effective_chat.id]['ultima_actualizacion'])

		if int(t_time.total_seconds())//60 >= BotServer.__MIN_ACT:
			self.__actualizar_datos_grupo_handler(bot, update, chat_data)


		#	Realizar actualizaciones de los usuarios si hubiera pasado el tiempo
		#	mínimo requerido
		t_time = (datetime.datetime.now() -
		(chat_data['foros'][update.effective_chat.id]['miembros']
				[update.effective_user.id]['ultima_actualizacion']))

		if int(t_time.total_seconds())//60 >= BotServer.__MIN_ACT:
			self.__actualizar_datos_usuario_handler(bot,
													update.effective_user,
													update.effective_chat,
													chat_data)

		if not chat_data['foros'][update.effective_chat.id]['valido']:
			return

		#	Evaluar el mensaje para responderlo sólo si es académico
		academico = self.__score_message_callback(bot, update, chat_data)

		#	Almacenar el mensaje en la base de datos
		self.__registrar_mensaje(mensaje=mensaje_dato,
									academico=academico,
									recibido=True)

		if not academico:
			return

		#	Tratar de tomar la pregunta si se ha usado un comando
		m = re.search('/ask( )*(.*)', mensaje)

		if m:
			pregunta = m.group(2)
		else:
			#	Tomar la pregunta si se llama al profesor
			m = re.search(('^(profe(s{1,2}or)?|@%s),?( )*(.*)' %
												bot.get_me().username), mensaje)

			if m:
				pregunta = m.group(4)

		#	Se considera el texto entero como pregunta si no empareja
		#	con ninguna expresión
		if not pregunta:
			pregunta = mensaje

		bot_men = bot.sendMessage(chat_id=update.message.chat_id,
									text='Un momento %s' % usuario)
		self.__registrar_mensaje(mensaje=bot_men, recibido=False)

		#	Programar una tarea encargada de buscar y enviar la respuesta
		self.__bot_updater.job_queue.run_once(
								callback=self.__answer_question_callback,
								when=0,
								context={
											'id_chat': id_chat_emisor,
											'usuario': usuario,
											'id_mens_resp': id_mensaje,
											'pregunta': pregunta
									}
								)

	def __answer_question_callback(self, bot, job):

		"""Función manejadora encargada de enviar una respuesta al usuario ante
		una pregunta efectuada por el mismo en un chat determinado
		"""

		if self.__debug_mode: t_inicio = time.time()
		self.__log.debug('Iniciada función "__answer_question_callback"'\
							' de "BotServer"')

		id_chat_emisor = job.context['id_chat']
		usuario_emisor = job.context['usuario']
		id_mens_resp = job.context['id_mens_resp']
		pregunta = job.context['pregunta']

		#	Buscar la respuesta a la pregunta en la base de datos
		respuesta = self.__quest_manager.ask(pregunta)

		try:
			#	Enviarla al usuario
			if respuesta:
				bot_men = bot.sendMessage(chat_id=id_chat_emisor,
									text='Bien %s' % usuario_emisor,
									reply_to_message_id=id_mens_resp)
				self.__registrar_mensaje(mensaje=bot_men, recibido=False)

				self.__send_contenido_into_messages(
										contenidos=respuesta,
										id_chat=id_chat_emisor,
										text_parse_mode=telegram.ParseMode.HTML)

				self.__bd_interface.addMensajeRespuesta(
													id_mensaje=id_mens_resp,
													pregunta=pregunta,
													respondido=bool(respuesta))
			else:
				bot_men = bot.sendMessage(
								chat_id=id_chat_emisor,
								text=u'Lo siento, no puedo responder a tu'\
										u' pregunta %s' % emojis.CARA_GOTA,
								reply_to_message_id=id_mens_resp)
				self.__registrar_mensaje(mensaje=bot_men, recibido=False)

		except Exception as e:
			self.__log.error('Se produjo un error con la pregunta "{}" '\
								'formulada por el usuario "{}" en el chat '\
								'"{}":\n{}'.format(pregunta, usuario_emisor,
													id_chat_emisor, str(e)))

		if self.__debug_mode:
			tiempo = time.time() - t_inicio
			self.__log.debug('Finalizada función "__answer_question_callback"'\
							' de "BotServer" en %f s' % tiempo)

	def __message_private_callback(self, bot, update, user_data):

		"""Función manejadora encargada de la recepción de un mensaje en un chat
			privado
		"""

		self.__log.debug(('Iniciada función manejadora'\
							' "__message_private_callback" de "BotServer" con'\
							' parámetros:\nupdate:%s\nuser_data:%s' %
							(str(update), str(user_data))))

		###	Para chats privados ###

		#	Tomar los datos del usuario, buscarlos si es necesario
		#	e introducirlos en contexto
		if 'usuario' not in user_data:
			user_data['usuario'] = self.__bd_interface.getUsuario(
													update.effective_user.id)
		else:
			return

		if not user_data['usuario'] or not user_data['usuario']['valido']:
			return

		#	Registrar el mensaje recibido en la base de datos
		if user_data['usuario'] and user_data['usuario']['tipo'] == 'alumno':
			self.__registrar_mensaje(update.message)

		self.__log.debug('Finalizada función manejadora'\
								' "__message_private_callback" de "BotServer"')

	def __message_group_callback(self, bot, update, chat_data):

		"""Función manejadora encargada de la recepción de un mnesaje en un chat
			de grupo
		"""

		self.__log.debug('Iniciada función manejadora'\
						' "__message_group_callback" de "BotServer" con'\
						' parámetros:\nupdate:%s\chat_data:%s' % (str(update),
																str(chat_data)))

		#	Cargar los datos del grupo y de sus participantes,
		self.__load_datos_grupo_callback(bot, update, chat_data)

		#	Registrar el foro si no estaba registrado
		self.__registro_foro_handler(bot, update, chat_data)


		#	Registrar al ususario que envía el mensaje si no estaba registrado
		self.__registrar_usuario_grupo_handler(bot, update.effective_user,
												update.effective_chat,
												chat_data)

		#	Registrar cada uno de los usuarios que pudieran haberse unido al
		#	grupo en este momento
		mensaje = update.message or update.edited_message
		for usuario in mensaje.new_chat_members:
			self.__registrar_usuario_grupo_handler(bot, usuario,
													update.effective_chat,
													chat_data)

		#	Realizar actualizaciones de los datos del grupo si hubiera
		#	pasado el tiempo mínimo requerido
		t_time = (datetime.datetime.now() -
		chat_data['foros'][update.effective_chat.id]['ultima_actualizacion'])

		if int(t_time.total_seconds())//60 >= BotServer.__MIN_ACT:
			self.__actualizar_datos_grupo_handler(bot, update, chat_data)

		#	Realizar actualizaciones de los usuarios si hubiera pasado el tiempo
		#	mínimo requerido
		t_time = (datetime.datetime.now() -
		(chat_data['foros'][update.effective_chat.id]['miembros']
				[update.effective_user.id]['ultima_actualizacion']))

		if int(t_time.total_seconds())//60 >= BotServer.__MIN_ACT:
			self.__actualizar_datos_usuario_handler(bot,
													update.effective_user,
													update.effective_chat,
													chat_data)

		if not chat_data['foros'][update.effective_chat.id]['valido']:
			return

		#	Comprobar si el mensaje pertenece al ámbito docente o no, dar
		#	los avisos correspondoentes al usuario si no pertenecen al ámbito
		#	académico y o expulsar al usuario
		academico = self.__score_message_callback(bot, update, chat_data)

		#	Registrar el mensaje recibido en la base de datos
		self.__registrar_mensaje(mensaje=update.message,
									mensaje_editado=update.edited_message,
									academico=academico)

		self.__log.debug('Finalizada función manejadora'\
							' "__message_group_callback" de "BotServer"')

	def __load_datos_grupo_callback(self, bot, update, chat_data):

		"""Función manejadora encargada de cargar los datos del foro actual
		y de sus miembros en los datos de contexto
		"""
		###	Para chats públicos ###

		#	Tomar los datos del foro e introducirlos en contexto o
		#	registrarlo si no existe
		if 'foros' not in chat_data:
			chat_data['foros'] = {}

		if (update.effective_chat.id not in chat_data['foros'] or
			not chat_data['foros'][update.effective_chat.id]):
			foro_datos = self.__bd_interface.getForo(update.effective_chat.id)

			if foro_datos:
				chat_data['foros'][update.effective_chat.id] = foro_datos
			else:
				chat_data['foros'][update.effective_chat.id] = {}
				return

		#	Se prepara una lista con todos los usuarios pertenecientes al foro
		if ('miembros' not in chat_data['foros'][update.effective_chat.id] or
			not chat_data['foros'][update.effective_chat.id]['miembros']):
			(chat_data['foros'][update.effective_chat.id]
					['miembros']) = self.__bd_interface.listUsuarios_in_Foro(
													update.effective_chat.id)

			if not (chat_data['foros'][update.effective_chat.id]
					['miembros']):
				(chat_data['foros'][update.effective_chat.id]
						['miembros']) = {}

			#	Añadir fecha de última actualización a los usuarios
			fecha_actual = datetime.datetime.now()

			for m in chat_data['foros'][update.effective_chat.id]['miembros']:
				(chat_data['foros'][update.effective_chat.id]['miembros']
									[m]['ultima_actualizacion']) = fecha_actual

		if 'ultima_actualizacion' not in (chat_data['foros']
													[update.effective_chat.id]):
			(chat_data['foros'][update.effective_chat.id]
			['ultima_actualizacion']) = datetime.datetime.now()

	def __registro_foro_handler(self, bot, update, chat_data):

		"""Función manejadora que se encarga de registrar un foro docente
			Nota: Requiere haber usado anteriormente
			"__load_datos_grupo_callback"
		"""

		if (update.effective_chat.id not in chat_data['foros'] or
			not chat_data['foros'][update.effective_chat.id]):
			#	Registrar el grupo docente
			#	(se delega a la callback correspondiente)
			try:
				self.__bd_interface.addForo(id_chat=update.effective_chat.id,
											nombre=update.effective_chat.title,
											tipo=update.effective_chat.type,
											valido=False,
											fecha_creacion=
														datetime.datetime.now())

				(chat_data['foros']
				[update.effective_chat.id]) = self.__bd_interface.getForo(
											foro_id=update.effective_chat.id)

				(chat_data['foros'][update.effective_chat.id]
							['ultima_actualizacion']) = datetime.datetime.now()
			except Exception as e:
				self.__log.error(('Error al registrar al foro %d'\
									', valor de excepción:\n%s' %
									(update.effective_chat.id, str(e))))
				return

		#	Se comprueba si el sistema hubiera sido nombrado administrador,
		#	y tuviera los permisos innecesarios, en caso contrario,
		#	se considera el grupo inválido
		if not chat_data['foros'][update.effective_chat.id]['valido']:
			if (update.effective_chat.get_member(bot.get_me().id) in
									update.effective_chat.get_administrators()):
				chat_data['foros'][update.effective_chat.id]['valido'] = True

				try:
					self.__bd_interface.editForo(update.effective_chat.id,
													valido=True)
				except Exception as e:
					self.__log.error(('Error al editar el foro %d para hacerlo'\
										' válido:\n%s' %
										(update.effective_chat.id, str(e))))

				(chat_data['foros'][update.effective_chat.id]
					['ultima_actualizacion']) = datetime.datetime.now()
			else:
				chat_data['foros'][update.effective_chat.id]['valido'] = False


	def __registrar_usuario_grupo_handler(self, bot, usuario, chat, chat_data):

		"""Permite efectuar el registro de un usuario y de su inscripción
			a un grupo.
			Nota: Se requiere haber usado previamente la función
			"__load_datos_grupo_callback"
		"""

		#	El usuario no está registrado en los datos de contexto y se
		#		asegura su registro en el sistema, su registro en el foro
		#		y su registro en los datos de contexto
		if (not 'miembros' in chat_data['foros'][chat.id] or
			not isinstance(
				chat_data['foros'][chat.id]['miembros'], dict)
				or usuario.id not in
					chat_data['foros'][chat.id]['miembros']):


			#	Comprobar que el usuario existe y registrarlo o hacerlo
			#	válido si fuera neecsario
			usuario_datos = self.__bd_interface.getUsuario(user_id=
													usuario.id)

			if not usuario_datos:
				try:
					self.__bd_interface.addUsuario(
									id_usuario=usuario.id,
									nombre=usuario.first_name,
									apellidos=usuario.last_name,
									username=usuario.username,
									id_chat=usuario.id,
									fecha_registro=datetime.datetime.now(),
									tipo='alumno')

				except Exception as e:
					self.__log.error('Error al tratar de registrar al usuario'\
									' "%s" con id %d. Valor de excepción: %s'% (
									usuario.full_name,
									usuario.id, str(e)))
					return
			elif not usuario_datos['valido']:
				try:
					self.__bd_interface.editUsuario(
											id_usuario=usuario.id,
											valido=True)
					usuario_datos['valido'] = True
				except Exception as e:
					self.__log.error('Error al editar al usuario "%s" con id %d'\
									' para hacerlo válido, valor de'\
									'excepción %s' % (
									usuario.full_name,
									usuario.id, str(e)))
					return


			#	Registrar al usuario en el foro
			try:
				self.__bd_interface.addUsuarioForo(
						id_chat=chat.id,
						usuarios=usuario.id)

				self.__log.info('Usuario %s con id %d ha sido registrado'\
								' en foro %s con id %d' % (usuario.full_name,
								usuario.id, chat.title, chat.id))

			except:
				self.__log.error('Error al insertar al usuario %s con id %d'\
									' en el foro %s con id %d' % (
										usuario.full_name,usuario.id,
										chat.title, chat.id))
				return

			(chat_data['foros'][chat.id]
					['miembros']) = self.__bd_interface.listUsuarios_in_Foro(
													chat.id)

			#	Añadir fecha de última actualización a los usuarios
			fecha_actual = datetime.datetime.now()

			for m in chat_data['foros'][chat.id]['miembros']:
				(chat_data['foros'][chat.id]['miembros']
									[m]['ultima_actualizacion']) = fecha_actual

			#	Hacer administradores a los docentes por ende
			if ((chat_data['foros'][chat.id]['miembros']
				[usuario.id]['tipo']) == 'docente' and
				chat.get_member(user_id=usuario.id) not
												in chat.get_administrators()):
				bot.promote_chat_member(user_id=usuario.id, chat_id=chat.id)

			try:
				self.__bd_interface.addEventoChatGrupal(
											tipo='registro',
											id_usuario=usuario.id,
											id_chat=chat.id,
											fecha=datetime.datetime.now())
			except Exception as e:
				self.__log.error('Error al tratar de registrar el "registro"'\
								' del usuario. Valor de excepción: %s' % str(e))

	def __actualizar_datos_grupo_handler(self, bot, update, chat_data):

		"""Se ocupa de detectar cambios en los datos de un chat grupal
			y de actualizar la información que se tiene sobre el mismo,
			además de actualizar los datos de contexto.

			Requiere haber usado previamente "__load_data_group_handler".
		"""

		chat = update.effective_chat

		if chat.type in ('channel', 'private'):
			return

		#	Comprobar si algún dato del grupo ha cambiado y proceder a editarlo
		if (chat.type != chat_data['foros'][chat.id]['tipo'] or
			chat.title != chat_data['foros'][chat.id]['nombre']):
			try:
				self.__bd_interface.editForo(
						id_chat=chat.id,
						nombre=chat.title,
						tipo='grupo' if chat.type == 'group' else 'supergrupo')
			except Exception as e:
				self.__log.error('Error al editar el foro con '\
									'id "{}":\n{}'.format(chat.id, str(e)))
				return

		#	Si alguien eliminara los permisos de Administración al sistema,
		#	este deja de ser considerado válido
		if (update.effective_chat.get_member(bot.get_me().id) not in
								update.effective_chat.get_administrators()):

			try:
				self.__bd_interface.editForo(
							id_chat=chat.id,
							valido=False)
			except Exception as e:
				self.__log.error('Error al editar el foro con '\
									'id "{}" para hacerlo '\
									'no válido:\n{}'.format(chat.id, str(e)))
				return
		#	Actualizar los datos de contexto de todas formas
		(chat_data['foros']
			[update.effective_chat.id]) = self.__bd_interface.getForo(
															foro_id=chat.id)

		#	Actualizar la lista de miembros preservando la fecha
		#	de última actualización de cada miembro
		aux_miembros = self.__bd_interface.listUsuarios_in_Foro(
												update.effective_chat.id)

		aux_miembros = aux_miembros if aux_miembros else {}

		if ('miembros' in chat_data['foros'][update.effective_chat.id] and
			chat_data['foros'][update.effective_chat.id]['miembros']):

			for m in aux_miembros:
				aux_miembros[m]['ultima_actualizacion'] = (chat_data['foros']
													[update.effective_chat.id]
													['miembros'][m]
													['ultima_actualizacion'])
		else:
			fecha_actual = datetime.datetime.now()

			for m in aux_miembros:
				aux_miembros[m]['ultima_actualizacion'] = fecha_actual

		(chat_data['foros'][update.effective_chat.id]
				['miembros']) = aux_miembros

		#	Anotar fecha de última actualización de los datos del foro
		(chat_data['foros'][update.effective_chat.id]
						['ultima_actualizacion']) = datetime.datetime.now()

	def __actualizar_datos_usuario_handler(self, bot, usuario, chat, chat_data):

		"""Se ocupa de detectar cambios en los datos de un usuario
			y de actualizar la información que se tiene sobre el mismo,
			además de actualizar los datos de contexto que se mantienen
			sobre él.

			Requiere haber usado previamente "__load_data_group_handler"
		"""

		if (usuario.first_name != (chat_data['foros'][chat.id]['miembros']
								[usuario.id]['telegram_user'].first_name) or
			usuario.last_name != (chat_data['foros'][chat.id]['miembros']
								[usuario.id]['telegram_user'].last_name) or
			usuario.username != (chat_data['foros'][chat.id]['miembros']
									[usuario.id]['telegram_user'].username)):
			try:
				self.__bd_interface.editUsuario(
										id_usuario=usuario.id,
										nombre=usuario.first_name,
										apellidos=usuario.last_name,
										username=usuario.username,
										id_chat=usuario.id)
			except Exception as e:
				self.__log.error('Se produjo un error al editar al usuario'\
									' "{}" con id {}:\n{}'.format(
										usuario.full_name, usuario.id, str(e)))
				return

		#	Actualizar los datos de contexto del usuario
		(chat_data['foros'][chat.id]['miembros']
				[usuario.id]) = self.__bd_interface.getUsuario(usuario.id)

		(chat_data['foros'][chat.id]['miembros']
				[usuario.id]).update(
								self.__bd_interface.getUsuario_status_Foro(
									id_chat=chat.id, id_usuario=usuario.id))

		#	Añadir fecha de última actualización a los usuarios
		(chat_data['foros'][chat.id]['miembros']
			[usuario.id]['ultima_actualizacion']) = datetime.datetime.now()

	def __score_message_callback(self, bot, update, chat_data):

		"""Función manejadora encargada de realizar la evaluación de los
			mensajes recibidos por el alumnado en chats grupales, reprender al
			usuario si detecta el envío de un mensaje no autorizado y llevar
			a cabo su baneo si duera necesario
		"""

		#	Sólo se realiza esta peración con los alumnos
		if (chat_data['foros'][update.effective_chat.id]['miembros']
						[update.effective_user.id]['tipo']) != 'alumno':
			return True

		academico = True
		mensaje = update.message or update.edited_message


		if not mensaje.text:
			return academico

		#	Evaluar el mensaje para conocer si es académico
		score = self.__speech_handler.evaluate(mensaje.text)

		self.__log.debug(('Mensaje recibido del usuario %s con id {} en el'\
							'grupo "{}" con id {} con certeza de pertenenencia'\
							' al tema tratado en el foro de {}'.format(
							update.effective_user.full_name,
								update.effective_user.id,
								update.effective_chat.title,
								update.effective_chat.id, score)))

		if score is not None and score < self.__config['umbral_eval_conv']:

			#	Actualizar los datos de contexto para evitar regañar a un
			#	antiguo usuario alumno que fue registrado hace poco
			#	como usuario docente
			self.__actualizar_datos_usuario_handler(bot, update.effective_user,
													update.effective_chat,
													chat_data)

			#	Volver a comprobar si de verdad es alumno
			if (chat_data['foros'][update.effective_chat.id]['miembros']
							[update.effective_user.id]['tipo']) != 'alumno':
				try:
					self.__bd_interface.editUsuarioForo(
							id_chat=update.effective_chat.id,
							usuarios=update.effective_user.id,
							n_avisos=0,
							ban=False)
				except Exception as e:
					self.__log.error('Se produjo un error al editar al '\
										'Usuario "{}" con id {} en el foro '\
										'"{}" con id {}:\n{}'.format(
										update.effective_user.full_name,
										update.effective_user.id,
										update.effective_chat.title,
										update.effective_chat.id, str(e)))

				return True

			#	Registrar este nuevo aviso
			(chat_data['foros'][update.effective_chat.id]['miembros']
						[update.effective_user.id]['n_avisos']) += 1
			n_avisos = (chat_data['foros'][update.effective_chat.id]['miembros']
						[update.effective_user.id]['n_avisos'])
			try:
				self.__bd_interface.editUsuarioForo(
						id_chat=update.effective_chat.id,
						usuarios=update.effective_user.id,
						n_avisos=n_avisos)
			except Exception as e:
				self.__log.error('Se produjo un error al editar al '\
									'Usuario "{}" con id {} en el foro '\
									'"{}" con id {}:\n{}'.format(
									update.effective_user.full_name,
									update.effective_user.id,
									update.effective_chat.title,
									update.effective_chat.id, str(e)))
				return False

			if n_avisos >= self.__config['avisos_ban']:

				#	Registrar la expulsión del usuario
				try:
					self.__bd_interface.editUsuarioForo(
							id_chat=update.effective_chat.id,
							usuarios=update.effective_user.id,
							ban=True,
							n_avisos=0)
				except Exception as e:
					self.__log.error('Se produjo un error al editar al '\
										'Usuario "{}" con id {} en el foro '\
										'"{}" con id {}:\n{}'.format(
										update.effective_user.full_name,
										update.effective_user.id,
										update.effective_chat.title,
										update.effective_chat.id, str(e)))
					return False

				try:
					self.__bd_interface.addEventoChatGrupal(
											tipo='ban',
											id_usuario=update.effective_user.id,
											id_chat=update.effective_chat.id,
											fecha=mensaje.date)
				except Exception as e:
					self.__log.error('Se produjo un error al registrar '\
										'un evento de baneo sobre el usuario'\
										' "{}" con id {} en el foro '\
										'"{}" con id {}:\n{}'.format(
										update.effective_user.full_name,
										update.effective_user.id,
										update.effective_chat.title,
										update.effective_chat.id, str(e)))
					return False

				(chat_data['foros'][update.effective_chat.id]['miembros']
									[update.effective_user.id]['n_avisos']) = 0
				(chat_data['foros'][update.effective_chat.id]['miembros']
										[update.effective_user.id]['ban']) = True

			#	Regañar al usuario por enviar mensajes no permitidos
			if n_avisos < self.__config['avisos_ban']:

				self.__log.info('Número de avisos por envío de mensajes no'\
								' permitidos dado al usuario %s con id %d en'\
								' el grupo "%s" con id %d: %d'
						% (update.effective_user.full_name,
							update.effective_user.id,
							update.effective_chat.title,
							update.effective_chat.id, n_avisos))

				try:
					bot_men = bot.sendMessage(
							chat_id=mensaje.chat_id,
							text='Perdona [%s](tg://user?id=%d) %s%s'
									% (update.effective_user.first_name,
										update.effective_user.id,
										emojis.CARA_ENFADO,
										emojis.CARA_ENFADO),
							parse_mode=telegram.ParseMode.MARKDOWN)
					self.__registrar_mensaje(mensaje=bot_men, recibido=False)
						#reply_to_message_id=mensaje. message_id)

					bot_men = bot.sendMessage(
							chat_id=mensaje.chat_id,
							text='En este grupo sólo se permite tratar *temas '\
												'relacionados con la asignatura*',
							parse_mode=telegram.ParseMode.MARKDOWN)
					self.__registrar_mensaje(mensaje=bot_men, recibido=False)


					bot_men = bot.sendMessage(
							chat_id=mensaje.chat_id,
							text='He detectado un mensaje tuyo que no tiene que '\
									'ver con la asignatura, por lo que te ruego '\
									'que no mandes ese tipo de mensajes')
					self.__registrar_mensaje(mensaje=bot_men, recibido=False)


					bot_men = bot.sendMessage(
							chat_id=mensaje.chat_id,
							text=' *%dº aviso* ' % n_avisos,
							parse_mode=telegram.ParseMode.MARKDOWN)
					self.__registrar_mensaje(mensaje=bot_men, recibido=False)

				except Exception as e:
					self.__log.error('Se produjo un error al notificar aviso '\
										'por mensaje no perteneciente al '\
										'ámbito docente al Usuario'
										'"{}" con id {} en el foro "{}" con'\
										' id {}:\n{}'.format(
										update.effective_user.full_name,
										update.effective_user.id,
										update.effective_chat.title,
										update.effective_chat.id, str(e)))
					#	Aunque no se llegue a enviar el mensaje con la
					#	notificación de baneo, se continúa
			else:

				self.__log.info('Baneado el usuario %s con id %d en el grupo '\
								'"%s" con id %d por agotar el número de avisos'\
								' permitidos'
						% (update.effective_user.full_name,
							update.effective_user.id,
							update.effective_chat.title,
							update.effective_chat.id))

				try:
					bot_men = bot.sendMessage(
							chat_id=mensaje.chat_id,
							text='Bien [%s](tg://user?id=%d)'
									% (update.effective_user.first_name,
										update.effective_user.id),
							parse_mode=telegram.ParseMode.MARKDOWN)
					self.__registrar_mensaje(mensaje=bot_men, recibido=False)

					bot_men = bot.sendMessage(
						chat_id=mensaje.chat_id,
						text='En vista de que no quieres acatar las reglas '\
								'de uso de este grupo, tengo que *expulsarte*',
						parse_mode=telegram.ParseMode.MARKDOWN)
					self.__registrar_mensaje(mensaje=bot_men, recibido=False)

				except Exception as e:
					self.__log.error('Se produjo un error al notificar baneo '\
										'por mensaje no perteneciente al '\
										'ámbito docente al Usuario'
										'"{}" con id {} en el foro "{}" con'\
										' id {}:\n{}'.format(
										update.effective_user.full_name,
										update.effective_user.id,
										update.effective_chat.title,
										update.effective_chat.id, str(e)))
					#	Aunque no se llegue a enviar el mensaje con la
					#	notificación de baneo, se continúa

				if bot.kick_chat_member(
					chat_id=update.effective_chat.id,
					user_id=update.effective_user.id) == False:

					self.__log.error('Error al banear al usuario %s con id %d'\
										' en el grupo "%s" con id %d por'\
										'agotar el número de avisos permitidos'
							% (update.effective_user.full_name,
								update.effective_user.id,
								update.effective_chat.title,
								update.effective_chat.id))

				#	Borrar del contexto
				del (chat_data['foros'][update.effective_chat.id]
										['miembros'][update.effective_user.id])

			academico = False

		return academico

	def __start_command_group_callback(self, bot, update, chat_data):

		"""Función manejadora del uso del comando \\start que hace que el
			sistema salude al usuario alumno o docente en un chat grupal
		"""

		#	Cargar los datos del grupo y de sus participantes en contexto,
		self.__load_datos_grupo_callback(bot, update, chat_data)

		#	Registrar el foro si no estaba registrado
		self.__registro_foro_handler(bot, update, chat_data)


		#	Registrar al ususario que envía el mensaje si no estaba
		#	registrado
		self.__registrar_usuario_grupo_handler(bot, update.effective_user,
												update.effective_chat,
												chat_data)

		#	Registrar cada uno de los usuarios que pudieran haberse unido al
		#	grupo en este momento
		mensaje = update.message or update.edited_message
		for usuario in mensaje.new_chat_members:
			self.__registrar_usuario_grupo_handler(bot, usuario,
													update.effective_chat,
													chat_data)

		#	Realizar actualizaciones de los datos del grupo si hubiera
		#	pasado el tiempo mínimo requerido
		t_time = (datetime.datetime.now() -
		chat_data['foros'][update.effective_chat.id]['ultima_actualizacion'])

		if int(t_time.total_seconds())//60 >= BotServer.__MIN_ACT:
			self.__actualizar_datos_grupo_handler(bot, update, chat_data)


		#	Realizar actualizaciones de los usuarios si hubiera pasado el tiempo
		#	mínimo requerido
		t_time = (datetime.datetime.now() -
		(chat_data['foros'][update.effective_chat.id]['miembros']
				[update.effective_user.id]['ultima_actualizacion']))

		if int(t_time.total_seconds())//60 >= BotServer.__MIN_ACT:
			self.__actualizar_datos_usuario_handler(bot,
													update.effective_user,
													update.effective_chat,
													chat_data)

		if chat_data['foros'][update.effective_chat.id]['valido']:

			try:
				#	Para grupos
				bot_men = bot.sendMessage(
						chat_id=update.message.chat_id,
						text='Bienvenid@, soy %s (@%s) tu bot y profesor en '\
								'este grupo de alumn@s.' % (
														bot.get_me().first_name,
														bot.get_me().username))
				self.__registrar_mensaje(mensaje=bot_men, recibido=False)

				bot_men = bot.sendMessage(
						chat_id=update.message.chat_id,
						text='Tómate la libertad de hablar con tus compañer@s'\
								' y pregúntame cualquier duda de teoría que'\
								' tengas usando el comando \\ask o bien'\
								'escribiendo \"profe\" o \"profesor\" o lo que'\
								' veas seguido de la duda que tengas')
				self.__registrar_mensaje(mensaje=bot_men, recibido=False)

				#	Registrar el mensaje recibido en la base de datos
				self.__registrar_mensaje(mensaje=update.message,
											recibido=True, academico=True)
			except Exception as e:
				self.__log.error('Se produjo un error al enviar la respuesta'\
								' al comando \\start al usuario "{}" con '\
								'id {} en el foro "{}" con id {}:\n{}'.format(
								update.effective_user.full_name,
								update.effective_user.id,
								update.effective_chat.title,
								update.effective_chat.id, str(e)))

		return ConversationHandler.END

	def __start_command_private_callback(self, bot, update, user_data):

		"""Función manejadora del uso del comando \\start que hace que el
			sistema salude al usuario alumno y dispone el menú docente a los
			usuarios docentes
		"""

		#	En chats privados

		#	Tomar los datos del usuario, buscarlos si es necesario
		#	e introducirlos en contexto
		if 'usuario' not in user_data:
			user_data['usuario'] = self.__bd_interface.getUsuario(
												update.effective_user.id)

		#	El usuario es ignorado si no está registrado
		if not user_data['usuario'] or not user_data['usuario']['valido']:

			#	Borra los datos de contexto
			user_data.clear()
			return ConversationHandler.END

		if user_data['usuario']['tipo'] == 'alumno':
			try:
				#	En chats privados para usuarios alumnos
				bot.sendMessage(chat_id=update.message.chat_id,
								text='Bienvenid@, soy %s (@%s) tu bot y'\
									' profesor en este grupo de alumn@s.' % (
														bot.get_me().first_name,
														bot.get_me().username))
				bot.sendMessage(chat_id=update.message.chat_id,
								text='Tómate la libertad de preguntar '\
										'cualquier duda de teoría que tengas'\
										' usando el comando /ask o bien '\
										'escribiendo \"profe\" o \"profesor\"'\
										' o lo que veas seguido de la duda que'\
										' tengas.')
				bot.sendMessage(
						chat_id=update.message.chat_id,
						text='e.g. \"profe, ¿Cómo se declara una cadena?\"')

			except Exception as e:
				self.__log.error('Se produjo un error al enviar la respuesta'\
								' al comando \\start al usuario "{}" con '\
								'id {}:\n{}'.format(
								update.effective_user.full_name,
								update.effective_user.id, str(e)))

			#	Borrar los datos de contexto
			user_data.clear()
			return ConversationHandler.END

		else:
			try:
				#	En chats privados para usuarios docentes
				bot.sendMessage(
							chat_id=update.message.chat_id,
							text='Hola '+update.message.from_user.first_name)

				return self.__mostrar_menu_docente_callback(bot, update,
																	user_data)
			except Exception as e:
				self.__log.error('Se produjo un error al enviar la respuesta'\
								' al comando \\start al usuario "{}" con '\
								'id {}:\n{}'.format(
								update.effective_user.full_name,
								update.effective_user.id, str(e)))

				#	Borrar los datos de contexto
				user_data.clear()
				return ConversationHandler.END

	def __saludo_callback(self, bot, update, user_data):

		"""Función ecargada de saludar al usuario en los chats privados cuando
			este emite un mensaje diciendo Hola o similar
		"""

		#	Tomar los datos del usuario, buscarlos si es necesario
		#	e introducirlos en contexto
		if 'usuario' not in user_data:
			user_data['usuario'] = self.__bd_interface.getUsuario(
													update.effective_user.id)

		#	El usuario es ignorado si no está registrado
		if not user_data['usuario'] or not user_data['usuario']['valido']:

			#	Borra los datos de contexto
			user_data.clear()
			return ConversationHandler.END

		if user_data['usuario']['tipo'] == 'alumno':
			try:
				#	En chats privados para usuarios alumnos
				bot.sendMessage(
							chat_id=update.message.chat_id,
							text='Bienvenid@, soy %s (@%s) tu bot y profesor'\
									' en este grupo de alumn@s.' % (
														bot.get_me().first_name,
														bot.get_me().username))
				bot.sendMessage(
							chat_id=update.message.chat_id,
							text='Tómate la libertad de preguntar cualquier'\
									' duda de teoría que tengas usando el '\
									'comando /ask o bien escribiendo \"profe\"'\
									'o \"profesor\" o lo que veas seguido de '\
									'la duda que tengas.')
				bot.sendMessage(
							chat_id=update.message.chat_id,
							text='e.g. \"profe, ¿Cómo se declara una cadena?\"')

			except Exception as e:
				self.__log.error('Se produjo un error al enviar la respuesta'\
								' al comando \\start al usuario "{}" con '\
								'id {}:\n{}'.format(
								update.effective_user.full_name,
								update.effective_user.id, str(e)))

			#	Borrar los datos de contexto
			user_data.clear()
			return ConversationHandler.END

		else:
			try:
				#	En chats privados para usuarios docentes
				bot.sendMessage(
							chat_id=update.message.chat_id,
							text='Hola '+update.message.from_user.first_name)

				return self.__mostrar_menu_docente_callback(bot, update,
																	user_data)

			except Exception as e:
				self.__log.error('Se produjo un error al enviar la respuesta'\
								' al comando \\start al usuario "{}" con '\
								'id {}:\n{}'.format(
								update.effective_user.full_name,
								update.effective_user.id, str(e)))

				#	Borrar los datos de contexto
				user_data.clear()
				return ConversationHandler.END


	def __mostrar_menu_docente_callback(self, bot, update, user_data):

		"""Función manejadora encargada de cargar el menú docente en la pantalla
			e iniciar la conversación en la que se desarrolla el funcionamiento
			de este menú
		"""

		chat_id = update.effective_chat.id

		try:
			bot.sendMessage(chat_id=chat_id,
							text='Selecciona la operación que deseas efectuar en'\
									' el menú',
							reply_markup=ReplyKeyboardMarkup(
												BotServer.__OPCIONES_MENU_PRINCIPAL,
												one_time_keyboard=True))

			return BotServer.__SELECT_OP_MENU_PRINCIPAL

		except Exception as e:
			self.__log.error('Se produjo un error al mostrar menú docente')
			user_data.clear()
			return ConversationHandler.END

	def __gestion_grupo_docente_callback(self, bot, update, user_data):

		"""Función manejadora encargada de disponer la lista de foros docentes
			al usuario docente con los botones correspondientes para ejecutar
			diferentes acciones sobre los mismos
		"""
		try:
			# Eliminar los botones del menú principal
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Estos son los foros docentes que existen:',
							reply_markup=ReplyKeyboardRemove())

			# Buscar los foros docentes TODO
			foros = self.__bd_interface.listForos()

			# Si no hay foros finaliza la función
			if not foros:
				bot.sendMessage(chat_id=update.message.chat_id,
								text='No existe ningún foro docente')

				user_data.clear()
				return ConversationHandler.END

			# Almacenar el resultado de la consulta en contexto
			user_data['lista_foros'] = foros

			# Listarlos
			for grupo in foros.keys():

				#	Se ignoran los foros en los que el sistema
				#	no sea administrador
				if foros[grupo]['valido'] == False:
					continue

				#	Generar los botones inline
				botones = InlineKeyboardMarkup(
					[[InlineKeyboardButton(('Obtener enlace invitación %s' %
																emojis.ENLACE),
										callback_data='Enlace/'+str(grupo))],

					[InlineKeyboardButton('Gestionar %s' % emojis.LLAVE_INGLESA,
										callback_data='Gestionar/'+str(grupo)),
					InlineKeyboardButton('Eliminar %s' % emojis.EQUIS_ROJA,
										callback_data='Eliminar/'+str(grupo))]])

				#	Mostrar la entrada por pantalla
				bot.sendMessage(chat_id=update.message.chat_id,
								text=foros[grupo]['nombre'],
								reply_markup=botones)

			# Botón para vover
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Para volver atrás',
							reply_markup=InlineKeyboardMarkup(
										[[InlineKeyboardButton(
											'Volver %s' % emojis.FLECHA_DER_IZQ,
													callback_data='Volver')]]))

			return BotServer.__SELECT_OP_GEST_DOCENTE

		except Exception as e:
			self.__log.error('Se produjo un error al mostrar la lista de'\
										' foros docentes:\n{}'.format(str(e)))
			user_data.clear()
			return ConversationHandler.END

	def __programar_comunicado_callback(self, bot, update, user_data):

		"""Función manejadora encargada de iniciar el cuestionario de introcción
			de contenidos que constituirán el cuerpo del comunciado a programar
		"""

		try:
			# Comprobar que exista algún foro previamente
			foros = self.__bd_interface.listForos()

			if not foros:
				bot.sendMessage(
					chat_id=update.effective_chat.id,
					text='No se ha encontrado ningún foro %s'% emojis.CARA_GOTA)
				user_data.clear()
				return ConversationHandler.END


			user_data['prog_comunicado'] = {}
			user_data['prog_comunicado']['contenidos'] = []

			bot.sendMessage(chat_id=update.effective_chat.id,
							text='Ok. Envíame uno a uno cada mensaje, imagen,'\
								' vídeo, etc que quieras mandar al alumnado')

			bot.sendMessage(chat_id=update.effective_chat.id,
							text='Cuando termines pulsa Aceptar aquí, o pulsa'\
								' Cancelar para anular el envío del comunciado',
							reply_markup=
								InlineKeyboardMarkup(
											[[InlineKeyboardButton('Aceptar',
												callback_data='Aceptar'),
											InlineKeyboardButton('Cancelar',
												callback_data='Cancelar')]]))

			return BotServer.__PROG_COMUNICADO_CONTENIDO

		except Exception as e:
			self.__log.error('Se produjo un error al solicitar el envío del'\
							' contenido del comunicado:\n{}'.format(str(e)))
			user_data.clear()
			return ConversationHandler.END

	def __comunicado_contenido_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir los mensajes con los
			contenidos que conforman el cuerpo del comunicado
		"""

		if not update.edited_message:
			#	Se toma un nuevo mensaje recibido y se almacena
			mensaje = update.message
			user_data['prog_comunicado']['contenidos'].append(mensaje)

		elif update.edited_message and update.message:
			#	Se ha editado un mnesaje escrito

			for i in range(len(user_data['prog_comunicado']['contenidos'])):
				if (user_data['prog_comunicado']['contenidos'][i].message_id ==
											update.edited_message.message_id):
					(user_data['prog_comunicado']
									['contenidos'][i]) = update.edited_message
					break

		self.__log.debug('Añadido mensaje con los siguientes datos:\n%s'
							% str(mensaje))

	def __comunicado_conf_contenido(self, bot, update, user_data):

		"""Función manejadora encargada de confirmar o no el contenido
			establecido para un comunicado, recibiendo para ello las pulsaciones
			"Aceptar" o "Cancelar"
		"""

		#	Se toma la pulsación
		eleccion = update.callback_query.data

		if eleccion == 'Aceptar':
			try:
				# Listar los foros docentes existentes y meterlos en botones
				foros = self.__bd_interface.listForos()

				if not foros:
					bot.sendMessage(
						chat_id=update.effective_chat.id,
						text='No se ha encontrado ningún '\
													'foro %s'% emojis.CARA_GOTA)

					user_data.clear()
					return ConversationHandler.END

				#	Añadir campo que indica la selección o no de los grupos
				for foro in foros:
					foros[foro]['seleccionado'] = False

				user_data['prog_comunicado']['select_grupos_docentes'] = foros


				botones = BotServer.__make_check_buttons(
						user_data['prog_comunicado']['select_grupos_docentes'])

				#	Botón para aceptar y cancelar
				botones.append([InlineKeyboardButton('Guardar',
													callback_data='Guardar'),
								InlineKeyboardButton('Cancelar',
													callback_data='Cancelar')])

				# Preguntar los grupos docentes en los que se mandarán el comunicado
				bot.sendMessage(chat_id=update.effective_chat.id,
								text='Selecciona los grupos docentes en los '\
										'que se mandarán los comunicados',
								reply_markup=InlineKeyboardMarkup(botones))

				return BotServer.__PROG_COMUNICADO_SELECT_GRUPO

			except Exception as e:
				self.__log.error('Se produjo un error al solicitar los '\
									'grupos docentes a los que se emitirá '\
									'el comunicado:\n{}'.format(str(e)))
				user_data.clear()
				return ConversationHandler.END


		elif eleccion == 'Cancelar':
			try:
				#	Se cancela el envío del comunicado
				bot.sendMessage(chat_id=update.callback_query.message.chat.id,
								text='Ok. Comunicado anulado. No lo envío')

				#	Borrar datos de contexto
				del user_data['prog_comunicado']

				return self.__mostrar_menu_docente_callback(bot, update,
																	user_data)
			except Exception as e:
				self.__log.error('Se produjo un error en el envío de mensajes'\
								' que notifican la cancelación de un '\
								'comunicado:\n{}'.format(str(e)))
				user_data.clear()
				return ConversationHandler.END

	def __comunicado_select_grupo_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir las pulsaciones sobre
			el panel de selección de grupos docentes, así como las pulsaciones
			sobre los botones "Guardar" y "Cancelar"
		"""

		#	Se toma la pulsación
		eleccion = update.callback_query.data

		if eleccion == 'Guardar':

			try:
				#	Comprobar que se halla elegido al menos un grupo
				if not any( [(user_data['prog_comunicado']
								['select_grupos_docentes'][grupo]
								['seleccionado']) for grupo in (user_data
								['prog_comunicado']['select_grupos_docentes'])] ):

					bot.sendMessage(chat_id=update.effective_chat.id,
									text=(u'Debes elegir algún grupo de'\
											' alumn@s %s'% emojis.CARA_ENFADO))
					return BotServer.__PROG_COMUNICADO_SELECT_GRUPO


				# Preguntar la fecha en la que se mandará el comunicado
				bot.sendMessage(chat_id=update.effective_chat.id,
								text=u'Ok. %s Indicame la fecha en la que '\
									'quieres que se mande el '\
									'comunicado' % emojis.MANO_OK,
								reply_markup=ReplyKeyboardRemove())
				bot.sendMessage(chat_id=update.effective_chat.id,
								text='Puedes decirme cosas como:'\
								'\n· 20 de Febrero\n· 3 de Mayo\n· 6/5/2020\n'\
								'· Mañana\n· Dentro de 2 semanas\n'\
								'· Dentro de 5 meses',
								reply_markup=ReplyKeyboardRemove())

				return BotServer._PROG_COMUNICADO_CONF_FECHA

			except Exception as e:
				self.__log.error('Se produjo un error en el envío de los'\
								' mensajes que solicitan el establecimiento '\
								'de la fecha de inicio:\n{}'.format(str(e)))

				user_data.clear()
				return ConversationHandler.END

		elif eleccion == 'Cancelar':
			try:
				#	Se cancela el envío del comunicado
				bot.sendMessage(chat_id=update.callback_query.message.chat.id,
								text='Ok. Comunicado anulado. No lo envío')

				del user_data['prog_comunicado']

				return self.__mostrar_menu_docente_callback(bot, update,
																	user_data)

			except Exception as e:
				self.__log.error('Se produjo un error en el envío de mensajes'\
								' que notifican la cancelación de un '\
								'comunicado:\n{}'.format(str(e)))
				user_data.clear()
				return ConversationHandler.END

		else:
			#	Grupo docente marcado o desmarcado
			grupo = int(eleccion)
			valor = (user_data['prog_comunicado']['select_grupos_docentes']
														[grupo]['seleccionado'])

			(user_data['prog_comunicado']['select_grupos_docentes']
											[grupo]['seleccionado']) = not valor

			#	Regenerar el conjunto de botones con el marcado
			#	o desmarcado realizado
			botones = BotServer.__make_check_buttons(
						user_data['prog_comunicado']['select_grupos_docentes'])

			#		Botón para aceptar y cancelar
			botones.append([InlineKeyboardButton('Guardar',
													callback_data='Guardar'),
							InlineKeyboardButton('Cancelar',
													callback_data='Cancelar')])

			try:
				# Editar el mensaje con el panel de selección de foros docentes
				bot.edit_message_reply_markup(
							chat_id=update.callback_query.message.chat.id,
							message_id=update.callback_query.message.message_id,
							text='Selecciona los grupos docentes en los que se'\
									' mandarán los comunicados',
							reply_markup=InlineKeyboardMarkup(botones))
			except Exception as e:
				self.__log.error('Se produjo un error en la edición de los'\
						' botones de selección de grupo:\n{}'.format(str(e)))

				user_data.clear()
				return ConversationHandler.END

	def __comunicado_fecha_conf_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la fecha de envío del
			comunicado enviada por medio de un mensaje por el usuario docente
		"""

		#	Recibir el mensaje con la fecha y analizarlo
		mensaje = update.message.text
		mensaje = replaceSpeechNumber(mensaje)

		fecha = parseSpeechDate( mensaje )
		hora = parseSpeechTime( mensaje )

		try:
			if not fecha:
				bot.sendMessage(chat_id=update.message.chat.id,
								text='No te he entendido, vuelve a especificármela'\
									' de otra forma')

				return BotServer._PROG_COMUNICADO_CONF_FECHA

			#	Almacenar la fecha en los datos de contexto
			user_data['prog_comunicado']['fecha_hora'] = fecha.replace(hour=0,
																	minute=0)

			if hora:
				#	Si en la anterior expresión también se expresa la hora, se
				#	salta directamente a su función manejadora
				return self.__comunicado_hora_conf_callback(bot, update,
																	user_data)

			# Preguntar la hora en la que se emitirá el comunicado
			bot.sendMessage(chat_id=update.message.chat.id,
							text=u'Ok. %s Indicame la hora a la que se mandará'\
								' el comunicado' % emojis.MANO_OK)
			bot.sendMessage(chat_id=update.message.chat.id,
							text='Puedes decirme cosas como:\n· 11:30\n· 9 y'\
							' media de la noche\n· A mediodia\n· A medianoche\n'
							'· Dentro de 5 minutos\n· Dentro de tres horas')

			return BotServer.__PROG_COMUNICADO_CONF_HORA

		except Exception as e:
			self.__log.error('Se produjo un error en el envío de los '\
								'mensajes que solicitan la hora de envío del'\
								' comunicado:\n{}'.format(str(e)))

			user_data.clear()
			return ConversationHandler.END

	def __comunicado_hora_conf_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibie la hora de envío del
			comunicado enviada por medio de un mensaje por el usuario docente
		"""
		#	Recibir el mensaje con la hora y analizarlo
		mensaje = update.message.text

		hora = parseSpeechTime( replaceSpeechNumber(mensaje) )

		if not hora:
			try:
				bot.sendMessage(chat_id=update.message.chat.id,
								text='No te he entendido, vuelve a '\
										'especificármelo de otra forma')

				return BotServer.__PROG_COMUNICADO_CONF_HORA
			except Exception as e:
				self.__log.error('Se produjo un error en el envío de un '\
									'mensaje notificatorio:\n{}'.format(str(e)))

				user_data.clear()
				return ConversationHandler.END

		#	Almacenar la hora en los datos de contexto
		user_data['prog_comunicado']['fecha_hora'] += datetime.timedelta(
																hours=hora[0],
																minutes=hora[1])

		#	Lista de foros a los que se deberá de enviar
		ids_foro = []

		for grupo in (user_data['prog_comunicado']
											['select_grupos_docentes']).keys():

			if (user_data['prog_comunicado']['select_grupos_docentes']
											[grupo]['seleccionado']) == True:
				ids_foro.append(grupo)

		#	Introducir los datos del comunicado
		try:
			id_com = self.__bd_interface.addComunicado(
						fecha_envio=user_data['prog_comunicado']['fecha_hora'],
						id_docente_emisor=update.effective_user.id,
						ids_chat_foro=ids_foro)
		except Exception as e:
			self.__log.error('Se produjo un error al registrar un '\
								'comunicado para su envío en la fecha {}, en'\
								' los foros con id {} y programado por el '\
								'usuario docente "{}" con id {}'.format(
								user_data['prog_comunicado']['fecha_hora'],
								ids_foro, update.effective_user.full_name,
								update.effective_user.id))

			user_data.clear()
			return ConversationHandler.END

		for contenido in user_data['prog_comunicado']['contenidos']:

			try:
				#	Extraer todos los componentes de los mensajes del comunicado
				datos = self.__extract_contenido_mensaje(
								contenido,
								multimedia_filename='Comunicado=%d-' % id_com)

				#	Alamcenar todos los datos en el comunicado
				for d in datos:
					self.__bd_interface.addDato(
										dato=d,
										fecha_creacion=datetime.datetime.now(),
										id_comunicado=id_com)
			except Exception as e:
				self.__log.error('Se produjo un error en la extracción y/o'\
								' almacenamiento de un contenido del '\
								'comunicado:\n{}'.format(str(e)))
				continue

		#	Programar Job
		self.__bot_updater.job_queue.run_once(
							callback=self.__send_comunicado_callback,
							when=user_data['prog_comunicado']['fecha_hora'],
							context=id_com,
							name='Comunicado-%d' % id_com)

		try:
			bot.sendMessage(chat_id=update.effective_chat.id,
							text=u'Ok. Comunicado programado, cuando llegue '\
								'el momento lo enviaré %s' % emojis.MANO_OK)
		except Exception as e:
			self.__log.error('Se produjo un error al notificar un comunicado'\
							' programado con éxito. No obstante, el comunicado'\
							' se ha registrado con éxito:\n{}'.format(str(e)))

		#	Borrar datos de contexto
		del user_data['prog_comunicado']

		return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __make_check_buttons(enum: dict) -> list:

		"""
		Permite generar un conjunto de botones checkables "InlineKeyboardButton"
		a partir de una enumeración en la forma de un mapa con el par
		<nombre del campo>:True/False.

		Recibe:
			- enum: Diccionario con el par <nombre del campo>:<True/False> donde
					True se emplea para indicar que el campo está marcado y False
					desmarcado
		Devuelve:
			- Lista de botones generado
		"""

		botones = []

		for campo in enum.keys():

			#	Para cada campo de la enumeración, se añade un botón con el
			#		nombre del campo seguido de un "check button"

			botones.append([InlineKeyboardButton((enum[campo]['nombre']+
					' '+(emojis.MULTIPLICACION if (enum[campo]
									['seleccionado']) == 0 else emojis.CHECK)),
												callback_data=campo)])
		return botones

	def __send_comunicado_callback(self, bot, job):

		"""Función manejadora encargada de enviar un comunicado programado
			en los foros docentes correspondientes y en la fecha y hora
			especificadas
		"""

		self.__log.debug('Iniciada función "__send_comunicado_callback"'\
							' de "BotServer"')

		#	Tomar los datos del comunicado a emitir
		comunicado = self.__bd_interface.getComunicado(job.context)
		usuario_emisor = self.__bd_interface.getUsuario(
												comunicado['docente_emisor'])

		#	Comprobar que el comunicado exista
		if not comunicado:
			self.__log.error('Comunicado %d no existente' % job.context)
			return

		if usuario_emisor:
			self.__send_contenido_into_messages(
				contenidos={
							None: {
								'tipo_dato': 'texto',
								'contenido': '*Comunicado de %s*'
									% usuario_emisor['telegram_user'].full_name
							}
						},
				id_chat=list(comunicado['foros'].keys()))

		#	Mandar el comunciado a cada uno de los foros en los que
		#	estuviera programado
		self.__send_contenido_into_messages(
									comunicado['datos'],
									id_chat=list(comunicado['foros'].keys()))

		#	Eliminar comunicado de la base de datos
		self.__bd_interface.removeComunicado(id_comunicado=job.context)

		self.__log.debug('Finalizada función "__send_comunicado_callback"'\
							' de "BotServer"')

	def __gestion_comunicados_callback(self, bot, update, user_data):

		"""Función manejadora encargada de mostar la lista de comunicados
			con botones para realizar diversas acciones sobre los mismos
		"""
		self.__log.debug('Iniciada función "__gestion_comunicados_callback"'\
							' de "BotServer"')

		# Buscar las comunicados pendiente de envío
		comunicados = self.__bd_interface.listComunicados()

		try:
			if comunicados:

				# Eliminar los botones del menú principal
				bot.sendMessage(chat_id=update.message.chat_id,
								text='Estos son los comunicados que existen:',
								reply_markup=ReplyKeyboardRemove())

				if not comunicados:
					bot.sendMessage(chat_id=update.message.chat_id,
									text='No se ha programado ningún comunicado')

					return self.__mostrar_menu_docente_callback(bot, update,
																		user_data)


				user_data['comunicados'] = comunicados

				# Listarlos
				for c in comunicados:

					#	Generar los botones inline
					botones = InlineKeyboardMarkup(
						[[InlineKeyboardButton(u'Leer %s'% emojis.LIBRO_ABIERTO,
												callback_data='Leer/'+str(c)),
						InlineKeyboardButton(u'Eliminar %s' % emojis.EQUIS_ROJA,
											callback_data='Eliminar/'+str(c))]])

					#	Mostrar la entrada por pantalla
					if len(comunicados[c]['foros']) > 1:

						nombres_foros = [comunicados[c]['foros'][x]
										for x in comunicados[c]['foros'].keys()]

						bot.sendMessage(chat_id=update.message.chat_id,
										text='Comunicado programado el día %s'\
											' sobre los grupos:\n%s' % (
											comunicados[c]['fecha_envio'].strftime(
															'%d/%m/%Y a las %H:%M'),
											'\n'.join(nombres_foros)),
										reply_markup=botones)
					else:
						nombre_foro = list( comunicados[c]['foros'].values() )[0]

						bot.sendMessage(chat_id=update.message.chat_id,
										text='Comunicado programado el día %s'\
											' sobre el grupo \"%s\"' % (
											comunicados[c]['fecha_envio'].strftime(
															'%d/%m/%Y a las %H:%M'),
															nombre_foro),
										reply_markup=botones)

				# Botón para vover
				bot.sendMessage(chat_id=update.message.chat_id,
								text=u'O si lo prefieres %s:' % emojis.CARA_GUINO,
								reply_markup=InlineKeyboardMarkup(
									[[InlineKeyboardButton(
											'Nuevo comunicado %s' % emojis.MEGAFONO,
										callback_data='Nuevo_comunicado')],

									[InlineKeyboardButton(
											u'Volver %s' % emojis.FLECHA_DER_IZQ,
										callback_data='Volver')]]))

			else:
				bot.sendMessage(chat_id=update.message.chat_id,
							text='¿Quieres programar un *comunicado nuevo*?',
							parse_mode=telegram.ParseMode.MARKDOWN,
							reply_markup=InlineKeyboardMarkup(
							[[InlineKeyboardButton('Si', callback_data='Si'),
							InlineKeyboardButton('No', callback_data='No')]]))

		except Exception as e:
			self.__log.error('Se produjo un error en el envío de los mensajes'\
							' con el listado de comunicados pendientes de'\
							' envío:\n{}'.format(str(e)))

			user_data.clear()
			return ConversationHandler.END


		self.__log.debug('Finalizada función "__gestion_comunicados_callback"'\
							' de "BotServer"')

		return BotServer.__SELECT_OP_GEST_COMUNICADO

	def __select_op_gest_comunicado_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir una opción seleccionada
			sobre un comunicado de la lista de comunicados
		"""

		opcion = update.callback_query.data.split('/')[0]

		if opcion == 'Leer':
			return self.__leer_comunicado_callback(bot, update, user_data)
		elif opcion == 'Eliminar':
			return self.__eliminar_comunicado_callback(bot, update, user_data)
		elif opcion in ('Nuevo_comunicado', 'Si'):
			return self.__programar_comunicado_callback(bot, update, user_data)
		elif opcion in ('Volver', 'No'):
			return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __leer_comunicado_callback(self, bot, update, user_data):

		"""Función manejadora encargada de ejecutar la operación de leer
			comunicado a petición del usuario
		"""

		# Buscar el comunicado a leer
		comunicado = update.callback_query.data.split('/')[1]
		comunicado = int(comunicado)

		#	Tomar los datos del comunicado y enviarlos mediante mensajes
		datos_comunicado = self.__bd_interface.getComunicado(comunicado)['datos']

		try:
			if datos_comunicado:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='Este es el comunicado programado:')

				self.__send_contenido_into_messages(datos_comunicado,
													update.effective_chat.id)
			else:
				self.__log.error('Comunicado %d no encontrado' % comunicado)
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=(u'El comunicado ha desaparecido %s' %
																emojis.CARA_GOTA))
				return self.__mostrar_menu_docente_callback(bot, update, user_data)
		except Exception as e:
			self.__log.error('Se produjo un error en el envío de los mensajes'\
							' que informaban del contenido de un comunciado'\
							' seleccionado:\n{}'.format(str(e)))

			user_data.clear()
			return ConversationHandler.END

	def __eliminar_comunicado_callback(self, bot, update, user_data):

		"""Función manejadora encargada de disponer al usuario el menú de
			confirmación de eliminación de un comunicado cuando se selecciona
			la operación de eliminar
		"""

		comunicado = update.callback_query.data.split('/')[1]

		try:
			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='¿Estás seguro de que deseas *eliminar este'\
						' comunicado* programado para su envío el día %s?' % (
							(user_data['comunicados'][int(comunicado)]
							['fecha_envio'].strftime('%d/%m/%Y a las %H:%M'))),
							parse_mode=telegram.ParseMode.MARKDOWN,
							reply_markup=InlineKeyboardMarkup([
											[InlineKeyboardButton('Si',
												callback_data=comunicado+'/Si'),
											InlineKeyboardButton('No',
											callback_data=comunicado+'/No')]]))
		except Exception as e:
			self.__log.error('Se produjo un error al emitir el mensaje con'\
							' la confirmación de eliminación de un '\
							'comunicado seleccionado:\n{}'.format(str(e)))
			user_data.clear()
			return ConversationHandler.END

		return BotServer.__SELECT_OP_ELIM_COMUNICADO

	def __select_op_elim_comunicado_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la selección del menú de
			confirmación de la operación de eliminar comunicado
		"""

		comunicado, opcion = update.callback_query.data.split('/')

		if opcion == 'Si':
			#	Si el usuario elige "Si", se borra el comunicado
			self.__bd_interface.removeComunicado(id_comunicado=int(comunicado))
			nombre_comunicado = 'Comunicado-%s' % comunicado

			#	Eliminar comunicado de la lista de tareas
			if nombre_comunicado in self.__bot_updater.job_queue.jobs():
				self.__bot_updater.job_queue.jobs()[('Comunicado-%d' %
													comunicado)].removed = True

			try:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='Comunicado eliminado con éxito %s %s, '\
								'ya no se enviará' % (emojis.MANO_OK,
																emojis.MANO_OK))
			except Exception as e:
				self.__log.error('Se produjo un error en el mensaje de '\
								'notificación de eliminado de un'\
								' comunicado:\n{}'.format(str(e)))
		else:
			try:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Operación cancelada %s, comunicado no'\
							' eliminado, ya no se enviará' % emojis.EQUIS_ROJA)
			except Exception as e:
				self.__log.error('Se produjo un error en el mensaje de '\
								'notificación de cancelación del eminiado de '\
								'un comunicado:\n{}'.format(str(e)))

		return self.__mostrar_menu_docente_callback(bot, update, user_data)


	def __descargar_conversaciones_callback(self, bot, update, user_data):

		"""Función manejadora encargada de solicitar al usuario docente la fecha
			de inicio de la recopilación que desea efectuar al iniciar el
			proceso de descarga
		"""
		try:
			# Preguntar la fecha de inicio
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Ok. Indicame la fecha de inicio a partir de '\
								'la cual se empezarán a recopilar '\
								'las conversaciones',
							reply_markup=ReplyKeyboardRemove())
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Puedes decirme cosas como:'\
							'\n· 20 de Febrero\n· 3 de Mayo\n· 6/5/2020\n'\
							'· Mañana\n· Dentro de 2 semanas\n'\
							'· Dentro de 5 meses',
							reply_markup=ReplyKeyboardRemove())

			return BotServer.__DESC_CONVERS_CONF_FECHA_INICIO

		except Exception as e:
			self.__log.error('Se produjo un error en el envío de mensajes'\
							' que solicitan la fecha de inicio de una'\
							' recopilación:\n{}'.format(str(e)))
			return ConversationHandler.END

	def __desc_convers_conf_fecha_inicio_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la fecha de inicio
			introducida por el usuario
		"""

		user_data['desc_conversaciones'] = {}

		#	Recibir el mensaje con la fecha y analizarlo
		mensaje = update.message.text
		mensaje = replaceSpeechNumber(mensaje)

		fecha = parseSpeechDate(mensaje)
		hora = parseSpeechTime(mensaje)

		try:
			if not fecha:
				bot.sendMessage(chat_id=update.message.chat_id,
								text='No he entendido. ¿Podrías repetírmelo de'\
																' otra forma?')
				return BotServer.__DESC_CONVERS_CONF_FECHA_INICIO

			#	Anotar la fecha especificada
			user_data['desc_conversaciones']['fecha_hora_inicio'] = fecha.replace(
																		hour=0,
																	minute=0)

			if hora:
				return self.__desc_convers_conf_hora_inicio_callback(bot, update,
																	user_data)

			# Preguntar la hora inicial
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Ok. Indicame la hora de inicio a partir de'\
						' la cual se empezarán a recopilar las conversaciones')

			bot.sendMessage(chat_id=update.message.chat_id,
							text='Puedes decirme cosas como:\n· 11:30\n· 9 y'\
							'media de la noche\n· A mediodia\n· A medianoche\n'\
								'· Dentro de 5 minutos\n· Dentro de tres horas')

			return BotServer.__DESC_CONVERS_CONF_HORA_INICIO

		except Exception as e:
			self.__log.error('Se produjo un error en el envío de mensajes'\
						' que solicitan la hora de inicio:\n{}'.format(str(e)))

			user_data.clear()
			return ConversationHandler.END

	def __desc_convers_conf_hora_inicio_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la hora de inicio de la
			recopilación a efectuar
		"""

		#	Recibir el mensaje con la hora y analizarlo TODO
		mensaje = update.message.text
		hora = parseSpeechTime( replaceSpeechNumber(mensaje) )

		try:
			if not hora:
				bot.sendMessage(chat_id=update.message.chat_id,
								text='No he entendido. ¿Podrías repetírmelo de'\
											' otra forma?')
				return BotServer.__DESC_CONVERS_CONF_HORA_INICIO

			(user_data['desc_conversaciones']
			['fecha_hora_inicio']) += datetime.timedelta(hours=hora[0],
																minutes=hora[1])

			# Preguntar la fecha de fin
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Ok. Ahora indícame la fecha de fin de'\
													' recopilación de mensajes')

			return BotServer.__DESC_CONVERS_CONF_FECHA_FIN

		except Exception as e:
			self.__log.error('Se produjo un error en el envío de mensajes'\
						' que solicitan la fecha de fin:\n{}'.format(str(e)))

			user_data.clear()
			return ConversationHandler.END

	def __desc_convers_conf_fecha_fin_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la fecha de fin
			introducida por el usuario
		"""

		#	Recibir el mensaje con la fecha y analizarlo
		mensaje = update.message.text
		mensaje = replaceSpeechNumber(mensaje)

		fecha = parseSpeechDate(mensaje)
		hora = parseSpeechTime(mensaje)

		try:
			if not fecha:
				bot.sendMessage(chat_id=update.message.chat_id,
								text='No he entendido. ¿Podrías repetírmelo de'\
										' otra forma?')
				return BotServer.__DESC_CONVERS_CONF_FECHA_FIN

			user_data['desc_conversaciones']['fecha_hora_fin'] = fecha.replace(
																	hour=0,
																	minute=0)

			if hora:
				return self.__desc_convers_conf_hora_fin_callback(bot, update,
																		user_data)

			# Preguntar la hora inicial
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Ok. Indicame la hora de fin de recopilación'\
									' de mensajes')

			return BotServer.__DESC_CONVERS_CONF_HORA_FIN

		except Exception as e:
			self.__log.error('Se produjo un error en el envío de mensajes'\
						' que solicitan la hora de fin:\n{}'.format(str(e)))

			user_data.clear()
			return ConversationHandler.END

	def __desc_convers_conf_hora_fin_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la hora de inicio de la
			recopilación a efectuar y de disponer un panel de botones para
			ayudar al usuario a elegir el foro docente al cual se aplica la
			descarga
		"""

		#	Recibir el mensaje con la hora y analizarlo
		mensaje = update.message.text
		hora = parseSpeechTime( replaceSpeechNumber(mensaje) )

		if not hora:
			try:
				bot.sendMessage(chat_id=update.message.chat_id,
								text='No he entendido. ¿Podrías repetírmelo de'\
										' otra forma?')
				return BotServer.__DESC_CONVERS_CONF_HORA_FIN
			except Exception as e:
				self.__log.error('Se produjo un error en el envío de un'\
								' mensaje que solicita la reintroducción de la'\
								' hora de inicio:\n{}'.format(str(e)))
				user_data.clear()
				return ConversationHandler.END

		(user_data['desc_conversaciones']
		['fecha_hora_fin']) += datetime.timedelta(hours=hora[0],
															minutes=hora[1])

		if (user_data['desc_conversaciones']['fecha_hora_inicio'] >=
							user_data['desc_conversaciones']['fecha_hora_fin']):
			try:
				bot.sendMessage(chat_id=update.message.chat_id,
								text=('La fecha y hora de inicio *no puede ser ni'\
								' mayor ni igual* que la de fin %s' %
														emojis.CARA_SUFRIMIENTO),
								parse_mode=telegram.ParseMode.MARKDOWN)

				bot.sendMessage(chat_id=update.message.chat_id,
								text='Vuelve a indicarme la fecha de inicio')
			except Exception as e:
				self.__log.error('Se produjo un error en el envío de los'\
								' mensajes que advierten de la itroducción '\
								'de fechas y horas de inicio y fin '\
								'incorrectas:\n{}'.format(str(e)))
				user_data.clear()
				return ConversationHandler.END

			return BotServer.__DESC_CONVERS_CONF_FECHA_INICIO

		# Listar los foros docentes existentes y meterlos en botones
		foros = self.__bd_interface.listForos()
		user_data['desc_conversaciones']['lista_foros'] = foros

		if not foros:
			try:
				bot.sendMessage(chat_id=update.message.chat_id,
								text='No se ha encontrado ningún grupo docente')
			except Exception as e:
				self.__log.error('Se produjo un error en el envío del mensaje'\
								' que notifica la inexistencia de '\
								'foros docentes:\n{}'.format(str(e)))
			return self.__mostrar_menu_docente_callback(bot, update, user_data)

		botones = []

		for foro in foros:
			botones.append([InlineKeyboardButton(foros[foro]['nombre'],
														callback_data=foro)])

		try:
			# Preguntar el grupo docente
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Por último, pincha en el grupo docente sobre'\
											' el que deseas hacer la recopilación',
							reply_markup=InlineKeyboardMarkup(botones))

			#	Botón para cancelar
			bot.sendMessage(chat_id=update.message.chat_id,
							text='O pulsa "Cancelar" para salir',
							reply_markup=InlineKeyboardMarkup([[
											InlineKeyboardButton('Cancelar',
													callback_data='Cancelar')]]))
		except Exception as e:
			self.__log.error('Se produjo un error en el envío de mensajes '\
							'con botones que permiten seleccionar el'\
							' foro docente:\n{}'.format(str(e)))
			user_data.clear()
			return ConversationHandler.END

		return BotServer.__DESC_CONVERS_SELECT_GRUPO

	def __desc_convers_select_grupo_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la pulsación sobre el panel
			de selección del foro docente sobre el cual se emitirá el comunicado
			y de emitir un mensaje de confirmación
		"""

		#	Se recibe la pulsación
		grupo = update.callback_query.data

		if grupo == 'Cancelar':
			try:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Ok. En otro momento mejor %s'% emojis.MANO_OK)
			except Exception as e:
				self.__log.error('Se produjo un error en el envío de un mensaje')

			return self.__mostrar_menu_docente_callback(bot, update, user_data)
		else:

			user_data['desc_conversaciones']['foro'] = int(grupo)
			fecha_hora_inicio = (user_data['desc_conversaciones']
														['fecha_hora_inicio'])
			fecha_hora_fin = (user_data['desc_conversaciones']
														['fecha_hora_fin'])
			nombre_foro = (user_data['desc_conversaciones']['lista_foros']
														[int(grupo)]['nombre'])

			try:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Ok. Se realizará una recopilación para "%s" '\
									'que abarcará desde el día %s a las %s '\
									'hasta el día %s a las %s' % (nombre_foro,
									fecha_hora_inicio.strftime('%d/%m/%Y'),
									fecha_hora_inicio.strftime('%H:%M'),
									fecha_hora_fin.strftime('%d/%m/%Y'),
									fecha_hora_fin.strftime('%H:%M')))
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='¿Es correcto?',
							reply_markup=InlineKeyboardMarkup(
											[[InlineKeyboardButton('Si',
													callback_data=grupo+'/Si'),
											InlineKeyboardButton('No',
												callback_data=grupo+'/No')]]))

				return BotServer.__DESC_CONVERS_CONF_GRUPO

			except Exception as e:
				self.__log.error('Se produjo un error en el envío de los '\
								'mensajes de confirmación de la '\
								'recopilación:\n{}'.format(str(e)))
				user_data.clear()
				return ConversationHandler.END

	def __desc_convers_conf_grupo_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir las pulsaciones del
			mensaje de confirmación emitido tras seleccionar el grupo sobre
			el que se aplica la recopilación.
		"""

		self.__log.debug('Iniciada función'\
						'"__desc_convers_conf_grupo_callback" de "BotServer"')

		#	Se recibe la opción
		id_foro, opcion = update.callback_query.data.split('/')
		id_foro = int(id_foro)

		if opcion == 'Si':

			n_mensajes = self.__bd_interface.countMensajesForo(
				id_chat=user_data['desc_conversaciones']['foro'],
				fecha_inicio=user_data['desc_conversaciones']['fecha_hora_inicio'],
				fecha_fin=user_data['desc_conversaciones']['fecha_hora_fin'])

			try:
				#	Si no hay mensajes, no se realiza recopilación alguna
				if not n_mensajes:
					bot.sendMessage(
							chat_id=update.callback_query.message.chat_id,
							text=u'No hay nada que recopilar '+emojis.CARA_GOTA)
					return self.__mostrar_menu_docente_callback(bot, update,
																	user_data)

				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text=('Ok. %s Hago la recopilación y te la mando' %
																emojis.MANO_OK))
			except Exception as e:
				self.__log.error('Se produjo un error en el envío de los'\
								' mensajes que informan de la recopilación a'\
								' efectuar. No obstante, la recopilación se'\
								' registró con éxito:\n{}'.format(str(e)))

			self.__bot_updater.job_queue.run_once(
					callback=self.__desc_convers_recop_callback,
					when=0,
					context=
					{
						'foro': user_data['desc_conversaciones']['foro'],
						'usuario_docente_solicitante': user_data['usuario'],
						'id_chat_docente': update.callback_query.message.chat_id,
						'fecha_hora_inicio': (user_data['desc_conversaciones']
													['fecha_hora_inicio']),
						'fecha_hora_fin': (user_data['desc_conversaciones']
														['fecha_hora_fin']),
						'n_mensajes': n_mensajes
					},
					name=('Recopilacion-id_foro=%d-fecha_inicio=%s-fecha_fin=%s'%
						(user_data['desc_conversaciones']['foro'],
						user_data['desc_conversaciones']['fecha_hora_inicio'],
						user_data['desc_conversaciones']['fecha_hora_fin'])))

		else:
			try:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Ok. No hago la recopilación')
			except Exception as e:
				self.__log.error('Se produjo un error en el envío de un mensaje')

		self.__log.debug('Finalizada función'\
						' "__desc_convers_conf_grupo_callback" de "BotServer"')

		return self.__mostrar_menu_docente_callback(bot, update, user_data)


	def __desc_convers_recop_callback(self, bot, job):

		"""Función manejadora encargada de llevar a cabo la recopilación
			según lo establecido y mandarla al usuario
		"""

		self.__log.debug('Iniciada función "__desc_convers_recop_callback"'\
							' de "BotServer"')

		id_foro = job.context['foro']
		fecha_hora_inicio = job.context['fecha_hora_inicio']
		fecha_hora_fin = job.context['fecha_hora_fin']
		nombre_docente_solicitante = (job.context['usuario_docente_solicitante']
													['telegram_user'].full_name)
		n_mensajes = job.context['n_mensajes']
		id_chat_docente = job.context['usuario_docente_solicitante']['id_chat']

		nombre_foro = self.__bd_interface.getForo(foro_id=id_foro)['nombre']

		#	Tomar los nombres de los usuarios
		lista_usuarios = self.__bd_interface.listUsuarios_in_Foro(id_foro)
		nombres_usuarios = [(lista_usuarios[x]
						['telegram_user'].full_name) for x in lista_usuarios]

		try:
			recopilador = ConversationCompiler(
				conversation_directory=(self.__config['directorio_base']+
												'conversaciones_recopiladas/'),
				nombre_foro=nombre_foro,
				fecha_inicio=fecha_hora_inicio,
				fecha_fin=fecha_hora_fin,
				docente_solicitante=nombre_docente_solicitante,
				lista_usuarios=nombres_usuarios)

			#	Comprobar que no existiera previamente otra recopilación igual
			fichero = recopilador.getPreviousComp()

			if not fichero:

				# 	Comienza la recopilación
				recopilador.start()

				#	Se recopilan los mensajes dividiéndolos en particiones
				particiones = ((n_mensajes//BotServer.__DESC_CONV_PART) +
									bool(n_mensajes%BotServer.__DESC_CONV_PART))

				for i in range(particiones):

					mensajes_part = self.__bd_interface.getMensajesForo(
						id_chat=id_foro,
						fecha_inicio=fecha_hora_inicio,
						fecha_fin=fecha_hora_fin,
						division=BotServer.__DESC_CONV_PART,
						particion=i)


					#	Añadir mensajes a la recopilación
					recopilador.addMensaje(mensajes_part)

				#	Fin de recopilación
				fichero = recopilador.close()

		except Exception as e:
			self.__log.error('Se produjo un error al realizar '\
								'la recopilación con fecha de inicio {}, '\
								'fecha de fin {} sobre el foro docente "{}"'\
								' con id {}:\n{}'.format(fecha_hora_inicio,
								fecha_hora_fin, nombre_foro, id_foro, str(e)))
			return

		try:
			#	Enviar fichero con la recopilación al usuario
			self.__send_contenido_into_messages(
											{
												None:{
													'tipo_dato': 'documento',
													'contenido': fichero
												}
											},
											id_chat=id_chat_docente)

			bot.sendMessage(chat_id=id_chat_docente,
						text=('Ahí tienes la recopilación %s' %
														emojis.CARA_SONRIENTE))

			bot.sendMessage(chat_id=id_chat_docente,
						text='Descomprime el fichero y abre el archivo'\
								' *conversaciones.html* para leer las '\
									'conversaciones cómodamente desde el navegador',
						parse_mode=telegram.ParseMode.MARKDOWN)

		except Exception as e:
			self.__log.error('Se produjo un error al enviar el archivo de'\
							' la recopilación y/o los mensajes con '\
							'instrucciones sobre su uso:\n{}'.format(str(e)))

		self.__log.debug('Finalizada función "__desc_convers_recop_callback"'\
							' de "BotServer"')

	def __baja__callback(self, bot, update, user_data):

		"""Función manejadora encargada de enviar el mensaje de confirmación
			al usuario preguntándole si de verdad desea darse de baja como
			usuario docente
		"""

		try:
			# Eliminar los botones del menú principal
			bot.sendMessage(chat_id=update.message.chat_id,
								text=emojis.CARA_SUSTO+emojis.CARA_SUSTO)
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Si te das de baja, dejarás de tener permisos'\
									' para administrar a los grupos de alumn@s.',
							reply_markup=ReplyKeyboardRemove())

			bot.sendMessage(chat_id=update.message.chat_id,
							text=' ¿Estás realmente segur@ de que deseas'\
											' *DARTE DE BAJA COMO PROFESOR/A*?',
							parse_mode=telegram.ParseMode.MARKDOWN,
							reply_markup=InlineKeyboardMarkup(
								[[InlineKeyboardButton('Si',callback_data='Si'),
								InlineKeyboardButton('No',callback_data='No')]]))

			return BotServer.__SELECT_OP_BAJA

		except Exception as e:
			self.__log.error('Se produjo un error en el envío de los'\
							' mensajes que solicitaban la confirmación de '\
							'baja al usuario docente "{}" '\
							'con id {}:\n{}'.format(
							update.effective_user.full_name,
							update.effective_user.id, str(e)))
			return ConversationHandler.END

	def __select_op_baja_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la confirmación de baja de
			foro docente y de emitir una segunda confirmación
		"""

		opcion = update.callback_query.data

		try:
			if opcion == 'Si':
				#	Si el usuario elige "Si", se le vuelve a hacer la pregunta
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
						text=emojis.CARA_GRITO_SUSTO+emojis.CARA_GRITO_SUSTO)
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='¿Estás realmente seguro de que deseas'\
									' *dejar de ser profesor*?',
							parse_mode=telegram.ParseMode.MARKDOWN,
							reply_markup=InlineKeyboardMarkup(
								[[InlineKeyboardButton('Si',callback_data='Si'),
								InlineKeyboardButton('No',callback_data='No')]])
						)

				return BotServer.__SELECT_OP_BAJA_CONF

			else:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Operación cancelada, no has sido dado'\
											' de baja %s' % emojis.CARA_GOTA)

				return self.__mostrar_menu_docente_callback(bot, update,
																	user_data)

		except Exception as e:
			self.__log.error('Se produjo un error en el envío del mensaje '\
							'respuesta al primer mensaje de confirmación de '\
							'baja al usuario docente "{}" con '\
							'id {}:\n{}'.format(update.effective_user.full_name,
								update.effective_user.id, str(e)))

			return ConversationHandler.END

	def __select_op_baja_conf_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la opción del segundo
			cuadro de confirmación y dar de baja al usuario docente o no
		"""

		opcion = update.callback_query.data

		if opcion == 'Si':
			#	Si el usuario elige "Si", queda eliminado como usuario docente

			#	Actualizar al usuario a usuario alumno o hacerlo no válido
			try:

				if not self.__bd_interface.existsUsuarioAnyForo(
									user_data['usuario']['telegram_user'].id):
					self.__bd_interface.editUsuario(
								user_data['usuario']['telegram_user'].id,
								tipo='alumno',
								valido=False)
				else:
					self.__bd_interface.editUsuario(
								user_data['usuario']['telegram_user'].id,
								tipo='alumno')

				self.__log.info('Retirado al usuario %s del conjunto de'\
							' usuarios docentes' % (user_data['usuario']
												['telegram_user'].full_name))
			except Exception as e:
				self.__log.error('Error al retirar al usuario %s del'\
							' conjunto de usuarios docentes.'\
							'Código de error: %s' % (
							user_data['usuario']['telegram_user'].full_name,
							str(e)))

				user_data.clear()
				return ConversationHandler.END

			#	Despedirse del usuario

			try:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='Ya no eres profesor/ra')
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Adiós %s. Muchas gracias por usarme y'\
						' espero haberte sido de utilidad' % emojis.MANO_ADIOS)

			except Exception as e:
				self.__log.error('Se produjo un error al enviar el mensaje de'\
									' despedida al usuario docente "{}" con '\
									'id {}. No obstante, la operación se '\
									'completó con éxito:\n{}'.format(
									update.effective_user.full_name,
									update.effective_user.id, str(e)))

			user_data.clear()
			return ConversationHandler.END

		else:
			try:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Operación cancelada, no has sido dado '\
									'de  baja %s' % emojis.CARA_GOTA)
			except Exception as e:
				self.__log.error('Se produjo un error al enviar un mensaje')

			return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __salir_menu(self, bot, update, user_data):

		"""Función manejadora encargada de cerrar el menú docente
		"""

		try:
			# Eliminar los botones del menú principal
			bot.sendMessage(chat_id=update.message.chat_id,
							text=u'Si necesitas cualquier cosa'\
												' dímelo '+emojis.CARA_GUINO,
							reply_markup=ReplyKeyboardRemove())
		except Exception as e:
			self.__log.error('Se produjo un error al enviar el '\
								'mensaje de cierre del '\
								'menú docente:\n{}'.format(str(e)))

		user_data.clear()
		return ConversationHandler.END

	def __select_op_gest_docente_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la pulsación de la operación
			a realziar sobre los foros docentes
		"""

		opcion = update.callback_query.data.split('/')[0]

		if opcion == 'Enlace':
			return self.__obtener_enlace_callback(bot, update, user_data)
		elif opcion == 'Gestionar':
			return self.__gestion_alumnos_callback(bot, update, user_data)
		elif opcion == 'Eliminar':
			return self.__eliminar_grupo_callback(bot, update, user_data)
		elif opcion == 'Volver':
			del user_data['lista_foros']
			return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __obtener_enlace_callback(self, bot, update, user_data):

		"""Función manejadora encargada de hacer llegar al usuario docente un
			enlace de invitación por petición suya
		"""

		# Buscar el enlace del grupo buscado
		id_grupo = 	int(update.callback_query.data.split('/')[1])
		nombre_grupo = 	user_data['lista_foros'][id_grupo]['nombre']


		try:
			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Aquí tienes el enlace de invitación '\
									'de %s' % nombre_grupo)

			try:
				#	Se solicita el enlace
				enlace = bot.export_chat_invite_link(id_grupo)
			except Exception as e:
				self.__log.error('Se produjo un error al obtener el enlace de '\
									'invitación al foro docente "{}" '\
									'con id {}:\n{}'.format(nombre_grupo,
															id_grupo, str(e)))
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='Lo siento, por alguna razón no he podido'\
									' obtener el enlace de invitación '\
									'a "{}" {}{}'.format(
										nombre_grupo, emojis.CARA_SUFRIMIENTO,
										emojis.CARA_SUFRIMIENTO))
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='Prueba a intentarlo más tarde')

			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text=enlace)

			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Mandáselo a l@s alumn@s que quieran entrar '\
														'en este grupo docente')

		except Exception as e:
			self.__log.error('Se produjo un error al enviar los mensajes con'\
							' el enlace de invitación al foro "{}" con id {} '\
							'obtenido:\n{}'.format(nombre_grupo,
							id_grupo, str(e)))

		# Desbanear al usuario docente si estuviera baneado en dicho grupo
		status = self.__bd_interface.getUsuario_status_Foro(
					id_chat=id_grupo,
					id_usuario=update.effective_user.id)

		if status and status['ban']:

			try:

				bot.unban_chat_member(chat_id=id_grupo,
										user_id=update.effective_user.id)

				self.__bd_interface.editUsuarioForo(
								id_chat=id_grupo,
								usuarios=update.effective_user.id,
								ban=False)
			except Exception as e:
				self.__log.error('Error al tratar de desbanear al usuario'\
					' docente en el grupo con id %d. Código de error: %s' % (
															id_grupo, str(e)
															)
					)

		return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __eliminar_grupo_callback(self, bot, update, user_data):

		"""Función manejadora encargada de enviar un mensaje de confirmación al
			usuario en la operación de eliminar grupo
		"""

		id_grupo = update.callback_query.data.split('/')[1]
		nombre_grupo = user_data['lista_foros'][int(id_grupo)]['nombre']

		try:
			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Has solicitado eliminar el '\
												'grupo \"%s\".' % nombre_grupo)

			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Ten en cuenta que si borras \"%s\", todos'\
							' l@s alumn@s serán expulsados del mismo y el '\
							'grupo no se podrá volver a recuperar'%nombre_grupo)

			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='¿Estás seguro de que deseas borrar este'\
									' grupo docente?',
							reply_markup=InlineKeyboardMarkup(
										[[InlineKeyboardButton('Si',
												callback_data=id_grupo+'/Si'),
										InlineKeyboardButton('No',
											callback_data=id_grupo+'/No')]]))

			return BotServer.__SELECT_OP_ELIM_GRUPO

		except Exception as e:
			self.__log.error('Se produjo un error al emitir el mensaje de'\
								' confirmación de eliminación del foro '\
								'"{}" con id {}:\n{}'.format(nombre_grupo,
								id_grupo, str(e)))
			user_data.clear()
			return ConversationHandler.END

	def __select_op_elim_grupo_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la elección al mensaje de
			confirmación de eliminación de grupo y enviar un segundo mensaje
			de confirmación al usuario
		"""

		id_grupo, opcion = update.callback_query.data.split('/')
		nombre_grupo = user_data['lista_foros'][int(id_grupo)]['nombre']

		try:
			if opcion == 'Si':
				#	Si el usuario elige "Si", se le vuelve a hacer la pregunta
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=emojis.CARA_SUSTO+emojis.CARA_GRITO_SUSTO)
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='¿Estás realmente seguro de que deseas '\
												'borrar \"%s\"?' % nombre_grupo,
								reply_markup=InlineKeyboardMarkup(
										[[InlineKeyboardButton('Si',
												callback_data=id_grupo+'/Si'),
										InlineKeyboardButton('No',
											callback_data=id_grupo+'/No')]]))

				return BotServer.__SELECT_OP_ELIM_GRUPO_CONF

			else:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Operación cancelada, grupo'\
								' \"%s\" no eliminado'\
									'%s' % (nombre_grupo,emojis.CARA_GOTA))

				return self.__mostrar_menu_docente_callback(bot, update,
																	user_data)

		except Exception as e:
			self.__log.error('Se produjo un error en el envío del mensaje '\
							'de confirmación de eliminación del foro docente'\
							' "{}" con id {}:\n{}'.format(nombre_grupo,
							id_grupo, str(e)))

			user_data.clear()
			return ConversationHandler.END

	def __select_op_elim_grupo_conf_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la elección al segundo
			mensaje de confirmación de eliminación de grupo y llevar a cabo
			la eliminación del grupo si se decide continuar adelante
		"""

		id_grupo, opcion = update.callback_query.data.split('/')
		id_grupo = int(id_grupo)
		nombre_grupo = user_data['lista_foros'][id_grupo]['nombre']

		if opcion == 'Si':
			#	Si el usuario elige "Si", y se borra el grupo definitivamente

			#	Tomar a todos los usuarios registrados
			lista_usuarios = self.__bd_interface.listUsuarios_in_Foro(id_grupo)

			if lista_usuarios:

				#	No se borran los datos del foro, sino que se marca como
				#	no válido
				self.__bd_interface.editForo(id_chat=id_grupo, valido=False)
				self.__log.info('Foro docente "%s" con id %d'\
									'eliminado' % (nombre_grupo, id_grupo))


				#	Se expulsan a los usuarios del grupo de Telegram
				for usuario in lista_usuarios:

					try:
						self.__bd_interface.removeUsuarioForo(id_grupo, usuario)
						bot.kick_chat_member(chat_id=id_grupo, user_id=usuario)
					except Exception as e:
						self.__log.error('Error al expulsar al usuario con id'\
								' %d del grupo %s. Valor de error: %s' % (
												usuario, nombre_grupo, str(e)))

					#	Declarar al usuario no válido si ya no pertenece a
					#	ningún grupo
					if (lista_usuarios[usuario]['tipo'] == 'alumno' and
						not self.__bd_interface.existsUsuarioAnyForo(
								lista_usuarios[usuario]['telegram_user'].id)):

							self.__bd_interface.editUsuario(
								id_usuario=(lista_usuarios[usuario]
													['telegram_user'].id),
								valido=False)

			try:
				#	El bot sale del grupo
				try:
					bot.leave_chat(id_grupo)
				except Exception as e:
					self.__log.error('Se produjo un error al tratar de '\
									'abandonar el foro con id {}:\n{}'.format(
															id_grupo, str(e)))

					bot.sendMessage(chat_id=update.callback_query.message.chat_id,
									text='Se produjo un error cuando intentaba'\
									' salir de "{}" {}{}'.format(nombre_grupo,
										emojis.CARA_GOTA, emojis.CARA_GOTA))

				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=('Grupo \"%s\" eliminado definitivamente' %
																nombre_grupo))
			except Exception as e:
				self.__log.error('Se produjo un error al enviar un mensaje '\
								'informando del abandono del foro docente'\
								' "{}" con id {}:\n{}'.format(nombre_grupo,
															id_grupo, str(e)))

		else:
			try:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Operación cancelada, grupo \"%s\"'\
									' no eliminado %s' % (nombre_grupo,
									emojis.CARA_GOTA))
			except Exception as e:
				self.__log.error('Se produjo un error al enviar un mensaje '\
								'informando de la cancelación de eliminación '\
								'del grupo:\n{}'.format(str(e)))

		return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __gestion_alumnos_callback(self, bot, update, user_data):

		"""Función manejadora que se ocupa de listar al alumnado y de disponer
			botones debajo de cada alumno/a para gestionarlo
		"""

		id_grupo = update.callback_query.data.split('/')[1]
		nombre_grupo = user_data['lista_foros'][int(id_grupo)]['nombre']

		try:
			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Alumn@s en el grupo docente'\
													' "%s": ' % nombre_grupo)

			#	Consultar todos los alumnos inscritos en este foro
			alumnos = self.__bd_interface.listUsuarios_in_Foro(int(id_grupo),
															solo_alumnos=True)

			#	Almacenar la lista en contexto
			user_data['lista_alumnos'] = alumnos

			if not alumnos:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='No hay alumn@s en este '\
										'foro %s' % (emojis.CARA_GOTA))

				return self.__mostrar_menu_docente_callback(bot, update,
																	user_data)

			for alumno in alumnos.keys():

				#	Generar los botones inline
				if alumnos[alumno]['ban'] == False:
					botones = InlineKeyboardMarkup(
									[[InlineKeyboardButton(
										'Banear %s' % emojis.CANDADO_CERRADO,
										callback_data=('Banear/'+str(id_grupo)+
															'/'+str(alumno))),
									InlineKeyboardButton(
										'Eliminar del grupo %s' % emojis.BOMBA,
										callback_data=('Eliminar del grupo/'+
															str(id_grupo)+'/'+
															str(alumno)))]])

				else:
					botones = InlineKeyboardMarkup(
										[[InlineKeyboardButton(
										'Readmitir %s' % emojis.CANDADO_ABIERTO,
										callback_data=('Readmitir/'+
															str(id_grupo)+'/'+
															str(alumno))),
										InlineKeyboardButton(
										'Eliminar del grupo %s' % emojis.BOMBA,
										callback_data=('Eliminar del grupo/'+
															str(id_grupo)+'/'+
															str(alumno)))]])

				#	Mostrar información del alumnado
				if not alumnos[alumno]['telegram_user'].username:
					bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=('Nombre: %s' %
								(alumnos[alumno]['telegram_user'].full_name)),
								reply_markup=botones)
				else:
					bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=('Nombre: %s\nusuario: %s' %
									(alumnos[alumno]['telegram_user'].full_name,
									alumnos[alumno]['telegram_user'].username)),
								reply_markup=botones)

			# Menú para vover
			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Para volver atrás',
							reply_markup=InlineKeyboardMarkup(
											[[InlineKeyboardButton(
											'Volver %s' % emojis.FLECHA_DER_IZQ,
													callback_data='Volver')]]))

			return BotServer.__SELECT_OP_GEST_ALUMNOS

		except Exception as e:
			self.__log.error('Se produjo un error al mostrar la lista de'\
							' alumn@s del foro "{}" con id {}:\n{}'.format(
											nombre_grupo, id_grupo, str(e)))
			user_data.clear()
			return ConversationHandler.END

	def __select_op_gest_alumnos_callback(self, bot, update, user_data):

		"""
			Función manejadora encargada de recibir la operación de gestión de
			alumnos/as seleccionada
		"""

		opcion = update.callback_query.data.split('/')[0]

		if opcion == 'Banear':
			return self.__banear_alumnos_callback(bot, update, user_data)
		elif opcion == 'Eliminar del grupo':
			return self.__eliminar_alumno_callback(bot, update, user_data)
		elif opcion == 'Readmitir':
			return self.__readmitir_alumnos_callback(bot, update, user_data)
		elif opcion == 'Volver':
			del user_data['lista_foros']
			del user_data['lista_alumnos']
			return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __banear_alumnos_callback(self, bot, update, user_data):

		"""Función manejadora de la operación de baneo de un alumno/a y que se
			encarga de escribir un mensaje de confirmación
		"""

		id_grupo, id_alumno = update.callback_query.data.split('/')[1:]
		grupo = user_data['lista_foros'][int(id_grupo)]['nombre']
		alumno = user_data['lista_alumnos'][int(id_alumno)]['telegram_user'].full_name

		try:
			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
						text='¿Estás seguro de que deseas banear a %s de'\
										' este grupo docente?' % alumno,
						reply_markup=InlineKeyboardMarkup(
											[[InlineKeyboardButton('Si',
													callback_data=(id_grupo+'/'+
															id_alumno+'/Si')),
											InlineKeyboardButton('No',
													callback_data=(id_grupo+'/'+
														id_alumno+'/No'))]]))

			return BotServer.__SELECT_OP_BAN_ALUMNO
		except Exception as e:
			self.__log.error('Se produjo un error al mostrar el mensaje de'\
							' confirmación de la operación de '\
							'baneo:\n{}'.format(str(e)))
			user_data.clear()
			return ConversationHandler.END

	def __select_op_ban_alumno_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la opción del mensaje de
			confirmación de la operación de baneo dispuesto anteriormente y
			ejecutar la operación en caso afirmativo
		"""

		id_grupo, id_alumno, opcion = update.callback_query.data.split('/')
		id_grupo = int(id_grupo)
		id_alumno = int(id_alumno)

		grupo = user_data['lista_foros'][id_grupo]['nombre']
		alumno = user_data['lista_alumnos'][id_alumno]['telegram_user'].full_name

		if opcion == 'Si':
			#	Si el usuario elige "Si", se banea al alumno

			#	Se registra este hecho en la base de datos
			self.__bd_interface.editUsuarioForo(id_chat=id_grupo,
												usuarios=id_alumno,
												ban=True)

			try:
				#	Se ejecuta el baneo
				bot.kick_chat_member(chat_id=id_grupo,
									user_id=id_alumno)
			except Exception as e:
				self.__log.error('Se produjo un error al tratar de banear'\
								' al usuario "{}" con id {} del foro "{}"'\
								' con id {}:\n{}'.format(alumno, id_alumno,
													grupo, id_grupo, str(e)))
				user_data.clear()
				return ConversationHandler.END

			try:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='Alumn@ %s fue baneado, puedes volver a'\
										' readmitirl@ posteriormente' % alumno)
			except Exception as e:
				self.__log.error('Se produjo un error en el envío del mensaje'\
								' que notifica el baneo. No obstante, el/la'\
								' alumno/a fue baneado/a con'\
								' éxito:\n{}'.format(str(e)))

			#	Registrar este evento
			self.__bd_interface.addEventoChatGrupal(
										tipo='ban',
										id_usuario=id_alumno,
										id_chat=id_grupo,
										fecha=update.callback_query.message.date)
		else:
			try:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Operación cancelada, alumno \"%s\" no'\
									' banead@ %s' % (alumno,emojis.CARA_GOTA))
			except Exception as e:
				self.__log.error('Se produjo un error al notificar la '\
									'cancelación de la operación de '\
									'baneo:\n{}'.format(str(e)))

		#	Borrar la lista de foros y de alumnos del contexto
		del user_data['lista_foros']
		del user_data['lista_alumnos']

		return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __readmitir_alumnos_callback(self, bot, update, user_data):

		"""Función manejadora de la operación de readmisión de un alumno/a y
			que se encarga de escribir un mensaje de confirmación
		"""

		id_grupo, id_alumno = update.callback_query.data.split('/')[1:]
		grupo = user_data['lista_foros'][int(id_grupo)]['nombre']
		alumno = (user_data['lista_alumnos']
									[int(id_alumno)]['telegram_user'].full_name)

		try:
			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Vas a readmitir a %s en este'\
									'grupo docente' % alumno)

			botones = InlineKeyboardMarkup(
							[[InlineKeyboardButton('Si',
										callback_data=id_grupo+'/'+id_alumno+'/Si'),
							InlineKeyboardButton('No',
									callback_data=id_grupo+'/'+id_alumno+'/No')]])


			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='¿Estás seguro de que deseas *readmitir a %s*'\
												' en este grupo docente?' % alumno,
							parse_mode=telegram.ParseMode.MARKDOWN,
							reply_markup=botones)

			return BotServer.__SELECT_OP_READMITIR_ALUMNO
		except Exception as e:
			self.__log.error('Se produjo un error al enviar el mensaje de '\
							'confirmación de readmisión del usuario "{}" con '\
							'id {} del foro "{}" con id {}:\n{}'.format(alumno,
							id_alumno, grupo, id_grupo, str(e)))
			user_data.clear()
			return ConversationHandler.END

	def __select_op_readmitir_alumno_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la opción del mensaje de
			confirmación de la operación de readmisión dispuesto anteriormente y
			ejecutar la operación en caso afirmativo
		"""

		id_grupo, id_alumno, opcion = update.callback_query.data.split('/')
		id_grupo = int(id_grupo)
		id_alumno = int(id_alumno)

		grupo = user_data['lista_foros'][id_grupo]['nombre']
		alumno = user_data['lista_alumnos'][id_alumno]['telegram_user'].full_name
		id_chat_alumno = user_data['lista_alumnos'][id_alumno]['id_chat']


		if opcion == 'Si':
			#	Si el usuario elige "Si", se deshace el baneo al alumno

			#	Se registra este hecho en la base de datos
			self.__bd_interface.editUsuarioForo(id_chat=id_grupo,
												usuarios=id_alumno,
												ban=False,
												n_avisos=0)

			try:
				#	Se deshace el baneo
				bot.unban_chat_member(chat_id=id_grupo,
									user_id=id_alumno)
			except Exception as e:
				self.__log.error('Se produjo un error al deshacer el baneo del'\
								' usuario "{}" con id {} del foro "{}" '\
								'con id {}:\n{}'.format(alumno, id_alumno,
													grupo, id_grupo, str(e)))
				user_data.clear()
				return ConversationHandler.END

			try:
				#	Se envía invitación al usuario para volver
				try:
					bot.sendMessage(chat_id=id_chat_alumno,
									text='Has sido readmitido en "%s",'\
									' pincha en el enlace para volver' % (grupo))
					bot.sendMessage(chat_id=id_chat_alumno,
									text=bot.export_chat_invite_link(
																chat_id=id_grupo))
					bot.sendMessage(chat_id=update.callback_query.message.chat_id,
									text=u'Alumn@ %s readmitid@ %s' % (alumno,
															emojis.CARA_SONRIENTE))
				except Exception as e:
					self.__log.error('Usuario id: %d, nombre: %s - Un error se'\
									' produjo al tratar de enviar el enlace de'\
									' invitación al usuario readmitido %s'\
									' con id %d en el grupo %s con id %d - Valor'\
									' de la excepción: %s' % (
									update.effective_user.id,
									update.effective_user.full_name, alumno,
									id_alumno, grupo, id_grupo, str(e)))

					bot.sendMessage(chat_id=update.effective_chat.id,
									text='Lo siento %s%s' % (emojis.CARA_GOTA,
															emojis.CARA_GOTA))
					bot.sendMessage(chat_id=update.effective_chat.id,
									text='*No puedo enviar a %s el enlace de'\
												' invitación para volver*' % alumno,
									parse_mode=telegram.ParseMode.MARKDOWN)
					bot.sendMessage(chat_id=update.effective_chat.id,
									text='Te paso el enlace y tú se lo'\
									' haces llegar %s' % emojis.CARA_SUFRIMIENTO)
					bot.sendMessage(chat_id=update.effective_chat.id,
									text=bot.export_chat_invite_link(
																chat_id=id_grupo))
			except Exception as e:
				self.__log.error('Se produjo un error al enviar al usuario '\
								'docente "{}" con id {} el mensaje con el'\
								' enlace de invitación para readmitir al '\
								'usuario "{}" con id {} en el foro "{}" con'\
								' id {}:\n{}'.format(
								update.effective_user.full_name,
								update.effective_user.id, alumno, id_alumno,
								grupo, id_grupo, str(e)))

			#	Registrar este evento
			self.__bd_interface.addEventoChatGrupal(
										tipo='readmision',
										id_usuario=id_alumno,
										id_chat=id_grupo,
										fecha=update.callback_query.message.date)
		else:
			try:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Operación cancelada, alumno \"%s\"'\
								' no readmitid@ %s' % (alumno,emojis.CARA_GOTA))
			except Exception as e:
				self.__log.error('Se produjo un error al enviar mensaje con'\
								' la confirmación de readmisión al usuario '\
								'alumno "{}" con id {} en el foro docente "{}"'\
								' con id {}:\n{}'.format(alumno, id_alumno,
													grupo, id_grupo, str(e)))

		#	Borrar la lista de foros y de alumnos del contexto
		del user_data['lista_foros']
		del user_data['lista_alumnos']

		return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __eliminar_alumno_callback(self, bot, update, user_data):

		"""Función manejadora de la operación de eliminación definitiva de un
			alumno/a y que se encarga de escribir un mensaje de confirmación
		"""

		id_grupo, id_alumno = update.callback_query.data.split('/')[1:]
		grupo = user_data['lista_foros'][int(id_grupo)]['nombre']
		alumno = (user_data['lista_alumnos'][int(id_alumno)]
												['telegram_user'].full_name)

		try:
			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Has solicitado expulsar a \"%s\"'\
									' de este grupo docente.' % alumno)

			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='Ten en cuenta que si borras a \"%s\" de'\
								' este grupo, se eliminarán todos los datos'\
								' asociados para este grupo docente' % alumno)

			bot.sendMessage(chat_id=update.callback_query.message.chat_id,
							text='¿Estás seguro de que deseas *expulsar a'\
											' %s* de este grupo ?' % alumno,
							parse_mode=telegram.ParseMode.MARKDOWN,
							reply_markup=InlineKeyboardMarkup(
												[[InlineKeyboardButton('Si',
													callback_data=(id_grupo+'/'+
															id_alumno+'/Si')),
												InlineKeyboardButton('No',
													callback_data=(id_grupo+'/'+
														id_alumno+'/No'))]]))

			return BotServer.__SELECT_OP_ELIM_ALUMNO

		except Exception as e:
			self.__log.error('Se produjo un error al enviar un mensaje de '\
							'confirmación de la operación de expulsión del '\
							'foro docente "{}" con id {} al usuario "{}" '\
							'con id {}:\n{}'.format(grupo, id_grupo, alumno,
															id_alumno, str(e)))
			return ConversationHandler.END

	def __select_op_elim_alumno_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la opción del mensaje de
			confirmación de la operación de eliminación definitiva
			dispuesto anteriormente y mostrar un segundo mensaje de confirmación
		"""

		id_grupo, id_alumno, opcion = update.callback_query.data.split('/')
		grupo = user_data['lista_foros'][int(id_grupo)]['nombre']
		alumno = (user_data['lista_alumnos'][int(id_alumno)]
											['telegram_user'].full_name)

		if opcion == 'Si':
			try:
				#	Si el usuario elige "Si", se le vuelve a hacer la pregunta
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=emojis.CARA_SUSTO+emojis.CARA_GRITO_SUSTO)
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='¿Estás realmente segur@ de que deseas'\
							' *expulsar a \"%s\"* de este grupo docente?' % alumno,
								parse_mode=telegram.ParseMode.MARKDOWN,
								reply_markup=InlineKeyboardMarkup(
												[[InlineKeyboardButton('Si',
														callback_data=(id_grupo+
														'/'+id_alumno+'/Si')),
												InlineKeyboardButton('No',
														callback_data=(id_grupo+
														'/'+id_alumno+'/No'))]]))

				return BotServer.__SELECT_OP_ELIM_ALUMNO_CONF
			except Exception as e:
				self.__log.error('Se produjo un error al enviar un mensaje de '\
								'confirmación de la operación de expulsión del'\
								' foro docente "{}" con id {} al usuario "{}" '\
								'con id {}:\n{}'.format(grupo, id_grupo, alumno,
															id_alumno, str(e)))
				user_data.clear()
				return ConversationHandler.END
		else:
			try:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Operación cancelada, alumno \"%s\"'\
								' no eliminado %s' % (alumno, emojis.CARA_GOTA))

			except Exception as e:
				self.__log.error('Se produjo un error al enviar un mensaje de '\
								'cancelación de la operación de expulsión del'\
								' foro docente "{}" con id {} al usuario "{}" '\
								'con id {}:\n{}'.format(grupo, id_grupo, alumno,
															id_alumno, str(e)))

			del user_data['lista_foros']
			del user_data['lista_alumnos']

			return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __select_op_elim_alumno_conf_callback(self, bot, update, user_data):

		"""Función manejadora encargada de recibir la opción del segundo mensaje
			de confirmación de la operación de readmisión dispuesto
			anteriormente y ejecutar la operación en caso afirmativo
		"""

		id_grupo, id_alumno, opcion = update.callback_query.data.split('/')
		id_grupo = int(id_grupo)
		id_alumno = int(id_alumno)

		grupo = user_data['lista_foros'][id_grupo]['nombre']
		alumno = user_data['lista_alumnos'][id_alumno]['telegram_user'].full_name

		#	Comprobar si el alumno está en más de un grupo docente,
		#	 si no es así, se debe notificar al usuario de que el alumno
		#	 será eliminado junto con todos sus datos

		if opcion == 'Si':
			#	Si el usuario elige "Si", se le vuelve a hacer la pregunta
			#	Expulsar al alumno del grupo y borrarlo definitivamente si
			#	 procediera

			#	Se ejecuta la expulsión del grupo
			try:
				bot.kick_chat_member(chat_id=id_grupo,
									user_id=id_alumno)
			except Exception as e:
				self.__log.error('Se produjo un error al expulsar del'\
								' foro docente "{}" con id {} al usuario "{}" '\
								'con id {}:\n{}'.format(grupo, id_grupo, alumno,
															id_alumno, str(e)))
				user_data.clear()
				return ConversationHandler.END

			#	Registrar este borrado en la base de datos
			self.__bd_interface.removeUsuarioForo(id_chat=id_grupo,
															usuarios=id_alumno)

			#	Eliminar al alumno del registro de Usuarios si no pertenece
			#		a ningún grupo (considerarlo no válido)
			if not self.__bd_interface.existsUsuarioAnyForo(id_alumno):
				self.__bd_interface.editUsuario(id_usuario=id_alumno,
												valido=False)

			try:
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text='Alumn@ \"%s\" expulsado' % alumno)
			except Exception as e:
				self.__log.error('Se produjo un error al enviar un mensaje'\
								' confirmando la expulsión del'\
								' foro docente "{}" con id {} del usuario "{}" '\
								'con id {}. No obstante, la expulsión'\
								' se efectuó con éxito:\n{}'.format(grupo,
										id_grupo, alumno, id_alumno, str(e)))
				user_data.clear()
				return ConversationHandler.END

			#	Registrar este evento
			self.__bd_interface.addEventoChatGrupal(
										tipo='expulsion',
										id_usuario=id_alumno,
										id_chat=id_grupo,
										fecha=update.callback_query.message.date)

		else:
			try:
				#	Si el usuario dice "No" se cancela la operación
				bot.sendMessage(chat_id=update.callback_query.message.chat_id,
								text=u'Operación cancelada, alumno \"%s\"'\
								' no expulsado %s' % (alumno, emojis.CARA_GOTA))
			except Exception as e:
				self.__log.error('Se produjo un error al enviar un mensaje'\
								' informando de la cacnelación de la expulsión'\
								' del foro docente "{}" con id {} del usuario '\
								'"{}" con id {}. No obstante, la expulsión'\
								' se efectuó con éxito:\n{}'.format(grupo,
										id_grupo, alumno, id_alumno, str(e)))
				user_data.clear()
				return ConversationHandler.END


		del user_data['lista_foros']
		del user_data['lista_alumnos']

		return self.__mostrar_menu_docente_callback(bot, update, user_data)

	def __menu_fallback_callback(self, bot, update):

		"""Función manejadora encargada de advertir al usuario ante la
			introducción de una opción no válida en el menú
		"""
		try:
			#	Fallback que se reproduce al introducir una acción inválida
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Opción %s no admitida' % update.message.text)
			bot.sendMessage(chat_id=update.message.chat_id,
							text='Ayúdate del menú para seleccionar una opción')
		except Exception as e:
			self.__log.error('Se produjo al enviar un'\
												' mensaje:\n{}'.format(str(e)))
			return ConversationHandler.END


	def __registro_usuario_docente(self, bot, update, user_data):

		"""
		Permite registrar a un usuario como usuario docente si ha introducido
		la clave de registro de usuario docente: usuario_docente_password
		"""

		self.__log.debug('Iniciada función manejadora '\
							'"__registro_usuario_docente" de "BotServer" con'\
							' los siguientes parámetros:\nupdate: '\
							'%s\nuser_data: %s' % (str(update), str(user_data)))

		#	Sólo se permite el registro en chats privados
		if update.message.chat.type != 'private':
			self.__log.debug('La función manejadora no se activa en un chat'\
							' privado. Se finaliza la ejecución de la función'\
							' manejadora "__registro_usuario_docente" de '\
							'"BotServer"')
			user_data.clear()
			return ConversationHandler.END

		#	Tomar los datos del usuario, buscarlos si es necesario
		# e introducirlos en contexto
		if 'usuario' not in user_data:
			self.__log.debug('Se recuperan datos de contexto del usuario')
			user_data['usuario'] = self.__bd_interface.getUsuario(
													update.effective_user.id)
		#	Aquí meter lo de válido o no
		#	El usuario se registra como usuario docente si no está registrado
		#		como usuario alumno o no está registrado
		if not user_data['usuario'] or user_data['usuario']['tipo'] == 'alumno':

			#	Se registra al usuario como usuario docente en la base de datos
			usuario = update.effective_user
			fecha_registro = datetime.datetime.now()
			id_chat = update.message.chat.id

			#	Notificar esta novedad a los usuarios
			#self.__bd_interface.addNovedad(textos='Usuari@ %s ha sido registrado como docente' % usuario.full_name)

			if not user_data['usuario']:
				self.__bd_interface.addUsuario(usuario.id,
												usuario.first_name,
												usuario.last_name,
												usuario.username,
												id_chat,
												fecha_registro,
												'docente')
				user_data['usuario'] = {}
			else:
				self.__bd_interface.editUsuario(usuario.id, tipo='docente')

			#	Se añade los nuevos datos del usuario al contexto
			user_data['usuario']['telegram_user'] = usuario
			user_data['usuario']['fecha_registro'] = fecha_registro
			user_data['usuario']['id_chat'] = id_chat
			user_data['usuario']['tipo'] = 'docente'

			self.__log.info('Usuario %s con id %d ha sido registrado como'\
						' "usuario docente"' % (usuario.full_name,usuario.id))

			try:
				bot.sendMessage(chat_id=update.message.chat_id,
								text=u'Bienvenid@ %s, has sido registrado como'\
								' usuario docente %s %s' % (usuario.full_name,
										emojis.MANO_ADIOS, emojis.MANO_ADIOS))
			except Exception as e:
				self.__log.error('Se produjo un error al enviar un mensaje'\
								' confirmando el registro como usuario docente'\
								' de "{}" con id {}:\n{}'.format(
								usuario.full_name, usuario.id, str(e)))

			return self.__mostrar_menu_docente_callback(bot, update, user_data)

		else:
			self.__log.debug('El usuario ya es un usuario docente y'\
						' no se registra. Se finaliza la ejecución de la'\
						'función manejadora "__registro_usuario_docente" de'\
						'"BotServer"')
			user_data.clear()
			return ConversationHandler.END

	def __entrada_grupo_callback(self, bot, update, chat_data):

		"""Función manejadora que se ocupa de registrar un nuevo foro en el
			cual ingresa el chat
		"""

		self.__log.debug('Iniciada función manejadora'\
							'"__entrada_grupo_callback" de "BotServer" con los'\
							' siguientes parámetros:\nupdate: '\
							'%s\nchat_data: %s' % (str(update), str(chat_data)))

		#	Se descarta la ejecución en grupos privados
		if update.message.chat.type in ('private', 'channel'):
			return

		#	Cargar los datos del foro en contexto si existieran
		self.__load_datos_grupo_callback(bot, update, chat_data)

		if ((update.effective_chat.id not in chat_data['foros']) or
			(not chat_data['foros'][update.effective_chat.id])):
			#	Llevar a cabo el registro del foro
			self.__registro_foro_handler(bot, update, chat_data)
		else:
			self.__actualizar_datos_grupo_handler(bot, update, chat_data)

		self.__log.info('Se ha detectado la entrada al foro %s con id %d'\
		 					' y se ha registrado dicho foro docente'% (
						update.effective_chat.title, update.effective_chat.id))

		self.__log.debug('Finalizada función manejadora'\
							'"__entrada_grupo_callback" de "BotServer" con los'\
							' siguientes parámetros:\nupdate: '\
							'%s\nchat_data: %s' % (str(update), str(chat_data)))


	def __enter_member_group_callback(self, bot, update, chat_data):

		"""Función manejadora del evento producido cuando un usuario entra en
			un foro docente
		"""

		self.__log.debug('Iniciada función manejadora'\
							' "__enter_member_group_handler" de "BotServer"'\
							'con los siguientes parámetros:\nupdate: '\
							'%s\nchat_data: %s' % (str(update), str(chat_data)))

		#	Cargar los datos del grupo en contexto
		self.__load_datos_grupo_callback(bot, update, chat_data)

		#	Tomar la lista de usuarios que ingresan en el foro
		usuarios_foro = update.message.new_chat_members

		if update.effective_chat.get_member(bot.get_me().id) in usuarios_foro:
			self.__entrada_grupo_callback(bot, update, chat_data)

		for usuario in usuarios_foro:

			try:
				#	Registrar a cada usuario o actualizarlo según proceda
				if usuario.id not in (chat_data['foros']
													[update.effective_chat.id]
																['miembros']):
					self.__registrar_usuario_grupo_handler(bot, usuario,
											update.effective_chat, chat_data)
				else:
					self.__actualizar_datos_usuario_handler(bot, usuario,
											update.effective_chat, chat_data)

				#	Registrar este evento
				self.__bd_interface.addEventoChatGrupal(
											tipo='entrada',
											id_usuario=usuario.id,
											id_chat=update.effective_chat.id,
											fecha=update.message.date)

				if chat_data['foros'][update.effective_chat.id]['valido']:
					try:
						#	Saludar al nuevo usuario que se acaba de registrar
						bot_men = bot.sendMessage(
									chat_id=update.message.chat.id,
									text='Hola %s %s, te damos la bienvenida a'\
											' %s %s.Soy %s (@%s).' % (
											usuario.full_name, emojis.MANO_ADIOS,
											update.message.chat.title,
											emojis.CARA_ALEGRE,
											bot.get_me().first_name,
											bot.get_me().username))
						self.__registrar_mensaje(mensaje=bot_men, recibido=False)

						bot_men = bot.sendMessage(
								chat_id=update.message.chat_id,
								text='Tómate la libertad de preguntar '\
									'cualquier duda de teoría que tengas '\
									'usando el comando /ask o bien escribiendo'\
									' \"profe\" o \"profesor\" o lo que veas'\
									' seguido de la duda que tengas.')
						self.__registrar_mensaje(mensaje=bot_men, recibido=False)

						bot_men = bot.sendMessage(
									chat_id=update.message.chat_id,
									text='e.g. \"profe, ¿Cómo se declara una'\
										' cadena?\"')
						self.__registrar_mensaje(mensaje=bot_men, recibido=False)

					except Exception as e:
						self.__log.error('Se produjo un error al enviar los'\
										' mensajes de saludo al usuario "{}" '\
										'con id {} por entrar en el foro "{}" '\
										'con id {}:\n{}'.format(
										usuario.full_name, usuario.id,
										update.message.chat.title,
										update.message.chat.id, str(e)))

					self.__log.info('Grupo id=%d, nombre grupo=%s - Registrada'\
										' la entrada del usuario %s con id %d' %
										(update.effective_chat.id,
										update.effective_chat.title,
										usuario.full_name,
										usuario.id))

			except Exception as e:
				self.__log.error('Grupo id=%d, nombre grupo=%s - Error al '\
								'manejar la entrada del usuario %s con id'\
								' %d\nValor de excepción: %s' % (
								update.effective_chat.id,
								update.effective_chat.title,
								update.effective_user.full_name,
								update.effective_user.id, str(e)))

		self.__log.debug('Finalizada función manejadora'\
							' "__enter_member_group_handler" de "BotServer"')

	def __exit_member_group_callback(self, bot, update, chat_data):

		"""Función manejadora del evento producido cuando un usuario sale de
			un foro docente
		"""

		self.__log.debug('Iniciada función manejadora '\
							'"__exit_member_group_callback" de "BotServer" '\
							'con los siguientes parámetros:\nupdate: '\
							'%s\nuser_data: %s' % (str(update), str(chat_data)))

		usuario_saliente = (update.message or
										update.edited_message).left_chat_member

		#	Tomar los datos del foro de contexto
		self.__load_datos_grupo_callback(bot, update, chat_data)

		try:
			if (update.effective_chat.id in chat_data['foros'] and
				chat_data['foros'][update.effective_chat.id]['valido']):
				#	Actualizar los datos del foro si fuera necesario
				self.__actualizar_datos_grupo_handler(bot, update, chat_data)

				if (usuario_saliente.id in (chat_data['foros']
					[update.effective_chat.id]['miembros']) and
					(chat_data['foros'][update.effective_chat.id]['miembros']
										[usuario_saliente.id]['valido'])):

					#	Actualizar los datos del usuario que abandona el foro
					self.__actualizar_datos_usuario_handler(bot,
													usuario_saliente,
													update.effective_chat,
													chat_data)

					#	Sólo queda determinar si el usuario salió del grupo
					#	porque fue baneado o salió por su propia cuenta
					if not (chat_data['foros'][update.effective_chat.id]
								['miembros'][usuario_saliente.id]['ban']):

						self.__bd_interface.removeUsuarioForo(
											id_chat=update.effective_chat.id,
											usuarios=usuario_saliente.id)

						self.__bd_interface.addEventoChatGrupal(
											tipo='salida',
											id_usuario=usuario_saliente.id,
											id_chat=update.effective_chat.id,
											fecha=update.message.date)

						#	Declarar al usuario como no válido si este era
						#	el último foro en el que se encontraba
						if ((chat_data['foros'][update.effective_chat.id]
							['miembros'][usuario_saliente.id]
							['tipo']) == 'alumno' and
							not self.__bd_interface.existsUsuarioAnyForo(
													usuario_saliente.id)):

								self.__bd_interface.editUsuario(
										id_usuario=usuario_saliente.id,
										valido=False)

						#	Eliminar usuario de los datos de contexto
						del (chat_data['foros'][update.effective_chat.id]
									['miembros'][usuario_saliente.id])

						self.__log.info('Usuario {} con id {} salió del '\
										'foro {} con id {}'.format(
										usuario_saliente.full_name,
										usuario_saliente.id,
										update.effective_chat.title,
										update.effective_chat.id))

		except Exception as e:
			self.__log.error('Error al registrar la salida del'\
								' Usuario {} con id {} en el grupo {} con'\
								' id {}\nValor de excepción: {}'.format(
									usuario_saliente.full_name,
									usuario_saliente.id,
									update.effective_chat.title,
									update.effective_chat.id,
									str(e)))

		self.__log.debug('Finalizada función manejadora '\
							'"__exit_member_group_callback" de "BotServer" ')

	def __exit_group_callback(self, bot, update, chat_data):

		"""Se ocupa de dar registrar el hecho de que el asistente sea
			expulsado de un foro docente
		"""

		self.__log.debug('Iniciada función manejadora '\
							'"__exit_group_callback" de "BotServer" '\
							'con los siguientes parámetros:\nupdate: '\
							'%s\chat_data: %s' % (str(update), str(chat_data)))

		#	Tomar los datos del foro de contexto
		self.__load_datos_grupo_callback(bot, update, chat_data)

		try:
			if (update.effective_chat.id in chat_data['foros'] and
				chat_data['foros'][update.effective_chat.id]['valido']):
				#	Actualizar los datos del foro si fuera necesario
				self.__bd_interface.editForo(id_chat=update.effective_chat.id,
											valido=False)

				if ('miembros' in (chat_data['foros']
					[update.effective_chat.id])):

					for miembro in (chat_data['foros']
										[update.effective_chat.id]['miembros']):

						self.__bd_interface.removeUsuarioForo(
										id_chat=update.effective_chat.id,
										usuarios=miembro)

						#	Declarar al usuario como no válido si este era
						#	el último foro en el que se encontraba
						if (chat_data['foros'][update.effective_chat.id]
							['miembros'][miembro]['tipo'] == 'alumno' and
							not self.__bd_interface.existsUsuarioAnyForo(
																	miembro)):

								self.__bd_interface.editUsuario(
										id_usuario=miembro,
										valido=False)

				self.__log.info('Se ha expulsado al sistema del foro {} '\
								'con id {} y ha sido desestimado '\
												'como foro docente'.format(
									update.effective_chat.full_name,
									update.effective_chat.id))
		except Exception as e:
			self.__log.error('Error al registrar la salida del'\
								' Usuario {} con id {} en el grupo {} con'\
								' id {}\nValor de excepción: {}'.format(
									update.effective_user.full_name,
									update.effective_user.id,
									update.effective_chat.title,
									update.effective_chat.id,
									str(e)))

		self.__log.debug('Finalizada función manejadora '\
							'"__exit_group_callback" de "BotServer" ')

	def __registrar_mensaje(self, mensaje=None, mensaje_editado=None,
								academico=True, recibido=True):

		"""Función manejadora encargada de registrar todos los datos del mensaje
			en la base de datos y/o en el directorio base del servidor si fuera
			necesario
		"""

		try:

			mensaje = mensaje or mensaje_editado
			editado = bool(mensaje_editado)

			if not mensaje:
				raise ValueError('"mensaje" o "mensaje_editado" deben de'\
									' ser proporcionados')

			#	Los eventos no se registran
			if not mensaje.effective_attachment and not mensaje.text:
				return

			#	Tomar el mensaje respondido si lo hubiera
			id_mensaje_respondido = mensaje.reply_to_message.message_id if mensaje.reply_to_message else None

			if mensaje.chat.type != 'private':

				if recibido:
					#	Registrar el mensaje recibido en la base de datos
					id_mensaje = self.__bd_interface.addMensaje(
							recibido=True,
							id_mensaje_chat=mensaje.message_id,
							id_usuario_emisor_receptor=mensaje.from_user.id,
							id_chat=mensaje.chat.id,
							editado=editado,
							id_mensaje_chat_respondido=id_mensaje_respondido,
							fecha=datetime.datetime.now(),
							academico=academico)

					multimedia_filename = 'mensaje=%d-id_grupo=%d-'\
											'id_mensaje_chat=%s' % (id_mensaje,
											mensaje.chat.id, mensaje.message_id)
				else:
					#	Registrar el mensaje enviado en la base de datos
					id_mensaje = self.__bd_interface.addMensaje(
									recibido=False,
									id_mensaje_chat=mensaje.message_id,
									id_chat=mensaje.chat.id,
									editado=editado,
									id_mensaje_chat_respondido=id_mensaje_respondido,
									fecha=datetime.datetime.now())

					multimedia_filename = 'mensaje=%d-id_grupo=%d-'\
											'id_mensaje_chat=%s' % (id_mensaje,
											mensaje.chat.id, mensaje.message_id)

			else:
				return

			#	Extraer todo el contenido del mensaje
			contenidos = self.__extract_contenido_mensaje(mensaje,
															multimedia_filename)
			#	Registrar todos los contenidos en la base de datos
			if contenidos:
				for c in contenidos:
					self.__bd_interface.addDato(dato=c,
												fecha_creacion=mensaje.date,
												id_mensaje=id_mensaje)

		except Exception as e:
			self.__log.error('Error al registrar el mensaje:\n%s' % str(e))

	def __save_contenido_file(self, filename, contenido):

		"""Se ocupa de almacenar el archivo asociado a los ficheros multimedia
			en el directorio base
		"""

		#	Descargar archivo e introducirlo en la ruta correspondiente

		if isinstance(contenido, telegram.PhotoSize):
			ruta_archivo = contenido.get_file().download(
						self.__config['directorio_base']+'imagenes/'+filename)
			mime_type = mimetypes.MimeTypes().guess_type(ruta_archivo)[0]
			file_id = contenido.get_file().file_id

			return ruta_archivo, mime_type, file_id
		elif isinstance(contenido, telegram.Document):
			ruta_archivo = contenido.get_file().download(
						self.__config['directorio_base']+'documentos/'+filename)
			mime_type = (contenido.mime_type or
							mimetypes.MimeTypes().guess_type(ruta_archivo)[0])
			file_id = contenido.get_file().file_id

			return ruta_archivo, mime_type, file_id
		elif isinstance(contenido, telegram.Video):
			ruta_archivo = contenido.get_file().download(
							self.__config['directorio_base']+'videos/'+filename)
			mime_type = (contenido.mime_type or
							mimetypes.MimeTypes().guess_type(ruta_archivo)[0])
			file_id = contenido.get_file().file_id

			return ruta_archivo, mime_type, file_id
		elif isinstance(contenido, telegram.Audio):
			ruta_archivo = contenido.get_file().download(
							self.__config['directorio_base']+'audios/'+filename)
			mime_type = (contenido.mime_type or
							(mimetypes.MimeTypes().guess_type(ruta_archivo)[0]))
			file_id = contenido.get_file().file_id

			return ruta_archivo, mime_type, file_id
		elif isinstance(contenido, telegram.VideoNote):
			ruta_archivo = contenido.get_file().download(
					self.__config['directorio_base']+'notas_video/'+filename)
			mime_type = mimetypes.MimeTypes().guess_type(ruta_archivo)[0]
			file_id = contenido.get_file().file_id

			return ruta_archivo, mime_type, file_id
		elif isinstance(contenido, telegram.Voice):
			ruta_archivo = contenido.get_file().download(
						self.__config['directorio_base']+'notas_voz/'+filename)
			mime_type = (contenido.mime_type or
							mimetypes.MimeTypes().guess_type(ruta_archivo)[0])
			file_id = contenido.get_file().file_id

			return ruta_archivo, mime_type, file_id
		elif isinstance(contenido, telegram.Sticker):
			ruta_archivo = contenido.get_file().download(
										(self.__config['directorio_base']+
											'stickers/'+contenido.set_name+'-'+
											filename))
			mime_type = mimetypes.MimeTypes().guess_type(ruta_archivo)[0]
			file_id = contenido.get_file().file_id

			return ruta_archivo, mime_type, file_id

		elif isinstance(contenido, telegram.Animation):
			ruta_archivo = self.__bot_interface.get_file(
												contenido.file_id).download(
										(self.__config['directorio_base']+
										'animaciones/'+filename))

			mime_type = contenido.mime_type or (mimetypes.MimeTypes().guess_type(
															ruta_archivo)[0])
			file_id = contenido.file_id

			return ruta_archivo, mime_type, file_id

		return None

	def __extract_contenido_mensaje(self, mensaje: telegram.Message,
										multimedia_filename=None,
										add_id_multimedia_file=True):

		"""Función manejadora encargada de extraer el contenido de un mensaje y
			almacenarlo apropiadamente en la base de datos y/o en el sistema
			de ficheros
		"""

		contenidos = []

		#	Extraer el texto del mensaje
		if mensaje.text:
			contenidos.append({
								'tipo_dato': 'texto',
								'contenido': mensaje.text
							})

		#	Extraer la imagen que el mensaje pudiera contener
		if mensaje.photo:

			if not multimedia_filename:
				raise valueError('Un nombre de fichero debe de ser '\
								'proporcionado para los archivos multimedia')

			ruta_archivo, mime_type, file_id = self.__save_contenido_file(
														(multimedia_filename+
	'-imagen=%s' % mensaje.photo[0].file_id if add_id_multimedia_file else ''),
							mensaje.photo[0])

			contenidos.append({
								'tipo_dato': 'imagen',
								'contenido': ruta_archivo,
								'file_id': file_id,
								'mime_type': mime_type
							})
		#	Extraer el vídeo que el mensaje pudiera contener
		if mensaje.video:

			if not multimedia_filename:
				raise valueError('Un nombre de fichero debe de ser '\
								'proporcionado para los archivos multimedia')

			ruta_archivo, mime_type, file_id = self.__save_contenido_file(
														(multimedia_filename+
		'-video=%s' % mensaje.video.file_id if add_id_multimedia_file else ''),
															mensaje.video)
			contenidos.append({
								'tipo_dato': 'video',
								'contenido': ruta_archivo,
								'file_id': file_id,
								'mime_type': mime_type
							})

		#	Extraer el audio que el mensaje pudiera contener
		if mensaje.audio:

			if not multimedia_filename:
				raise valueError('Un nombre de fichero debe de ser '\
								'proporcionado para los archivos multimedia')

			ruta_archivo, mime_type, file_id = self.__save_contenido_file(
														(multimedia_filename+
		'-audio=%s' % mensaje.audio.file_id if add_id_multimedia_file else ''),
															mensaje.audio)
			contenidos.append({
								'tipo_dato': 'audio',
								'contenido': ruta_archivo,
								'file_id': file_id,
								'mime_type': mime_type
							})

		#	Extraer la nota de voz que el mensaje pudiera contener
		if mensaje.voice:

			if not multimedia_filename:
				raise valueError('Un nombre de fichero debe de ser '\
								'proporcionado para los archivos multimedia')

			ruta_archivo, mime_type, file_id = self.__save_contenido_file(
														(multimedia_filename+
	'-nota_audio=%s' % mensaje.voice.file_id if add_id_multimedia_file else ''),
															mensaje.voice)
			contenidos.append({
								'tipo_dato': 'nota_voz',
								'contenido': ruta_archivo,
								'file_id': file_id,
								'mime_type': mime_type
							})

		#	Extraer la nota de vídeo que el mensaje pudiera contener
		if mensaje.video_note:

			if not multimedia_filename:
				raise valueError('Un nombre de fichero debe de ser '\
								'proporcionado para los archivos multimedia')

			ruta_archivo, mime_type, file_id = self.__save_contenido_file(
														(multimedia_filename+
'-nota_video=%s' % mensaje.video_note.file_id if add_id_multimedia_file else ''),
															mensaje.video_note)
			contenidos.append({
								'tipo_dato': 'nota_video',
								'contenido': ruta_archivo,
								'file_id': file_id,
								'mime_type': mime_type
							})

		#	Extraer la animación que el mensaje pudiera contener
		if mensaje.animation:

			if not multimedia_filename:
				raise valueError('Un nombre de fichero debe de ser '\
								'proporcionado para los archivos multimedia')

			ruta_archivo, mime_type, file_id = self.__save_contenido_file(
														(multimedia_filename+
'-animacion=%s' % mensaje.animation.file_id if add_id_multimedia_file else ''),
															mensaje.animation)
			contenidos.append({
								'tipo_dato': 'animacion',
								'contenido': ruta_archivo,
								'file_id': file_id,
								'mime_type': mime_type
							})

		#	Extraer el documento que el mensaje pudiera contener
		if mensaje.document:

			if not multimedia_filename:
				raise valueError('Un nombre de fichero debe de ser '\
								'proporcionado para los archivos multimedia')

			ruta_archivo, mime_type, file_id = self.__save_contenido_file(
														(multimedia_filename+
'-documento=%s' % mensaje.document.file_id if add_id_multimedia_file else ''),
															mensaje.document)
			contenidos.append({
								'tipo_dato': 'documento',
								'contenido': ruta_archivo,
								'file_id': file_id,
								'mime_type': mime_type
							})

		#	Extraer el sticker que el mensaje pudiera contener
		if mensaje.sticker:

			if not multimedia_filename:
				raise valueError('Un nombre de fichero debe de ser '\
								'proporcionado para los archivos multimedia')

			ruta_archivo, mime_type, file_id = self.__save_contenido_file(
															multimedia_filename,
															mensaje.sticker)
			contenidos.append({
								'tipo_dato': 'sticker',
								'contenido': ruta_archivo,
								'file_id': file_id,
								'mime_type': mime_type,
								'sticker_emoji': mensaje.sticker.emoji,
								'sticker_tipo': 'normal',
								'sticker_conjunto': mensaje.sticker.set_name
							})

		#	Extraer el contacto que el mensaje pudiera contener
		if mensaje.contact:
			contenidos.append({
								'tipo_dato': 'contacto',
								'telefono': mensaje.contact.phone_number,
								'nombre': mensaje.contact.first_name,
								'apellidos': mensaje.contact.last_name,
								'id_usuario': mensaje.contact.user_id,
								'vcard': mensaje.contact.vcard
							})

		#	Extraer la localización que el mensaje pudiera contener
		if mensaje.location:
			contenidos.append({
								'tipo_dato': 'localizacion',
								'longitud':mensaje.location.longitude,
								'latitud': mensaje.location.latitude
							})

		#	Extraer la avenida que el mensaje pudiera contener
		if mensaje.venue:
			contenidos.append({
								'tipo_dato': 'localizacion',
								'longitud':mensaje.venue.location.longitude,
								'latitud': mensaje.venue.location.latitude,
								'titulo': mensaje.venue.title,
								'direccion': mensaje.venue.address,
								'id_cuadrante': mensaje.venue.foursquare_id,
								'tipo_cuadrante': mensaje.venue.foursquare_type
							})

		return contenidos if contenidos else None

	def __send_contenido_into_messages(self, contenidos, id_chat,
								text_parse_mode=telegram.ParseMode.MARKDOWN):

		"""Se ocupa del envío de una serie de contenidos a uno o varios chats

			Parámetros:
			-----------
			contenidos: dict
				Diccionario ordenado constituído por el par:
				id_dato (int) - dato (dict)

				dato debe de contener los datos del contenido que se desea
				enviar.

				Por otra parte, si alguno de los contenidos enviados no están
				almacenados en la base de datos, id_dato debe de adoptar un
				valor None

			id_chat: list o int
				Identificadores de los chats en los que se desea enviar los
				contenidos

			text_parse_mode: telegram.ParseMode
				Tipo de parser usado para procesar los estilos de los textos
		"""

		self.__log.debug('Iniciada función "__send_contenido_into_message"'\
															' de "BotServer"')

		if type(id_chat) is int:
			id_chat = [id_chat]

		#	Sacar todos los contenidos y meterlos en mensajes
		for c in contenidos:

			try:

				#	El contenido tiene texto
				if contenidos[c]['tipo_dato'] == 'texto':
					for chat in id_chat:
						bot_men = self.__bot_interface.sendMessage(
											chat_id=chat,
											text=contenidos[c]['contenido'],
											parse_mode=text_parse_mode)
						self.__registrar_mensaje(mensaje=bot_men,
																recibido=False)

				elif contenidos[c]['tipo_dato'] in ('imagen', 'audio', 'video',
													'nota_audio', 'nota_voz',
													'documento', 'animacion',
													'sticker'):

					if 'file_id' in contenidos[c] and contenidos[c]['file_id']:
						#	Tratar de tomar el archivo de los servidores Telegram
						file_id = contenidos[c]['file_id']

						try:
							self.__bot_interface.get_file(file_id)
						except:
							self.__log.debug(('Archivo %s no encontrado en los'\
													' servidores de Telegram' %
													contenidos[c]['contenido']))
							file_id = None
					else:
						file_id = None

					for chat in id_chat:

						#	Enviar al primer chat
						if not file_id:
							#	Cargar el archivo desde el sistema de ficheros
							file_f = open(contenidos[c]['contenido'],'rb')
						else:
							file_f = file_id

						if contenidos[c]['tipo_dato'] == 'imagen':
							bot_men = self.__bot_interface.sendPhoto(
															chat_id=chat,
															photo=file_f,
															timeout=60
															)
							file_id = bot_men.photo[0].file_id
							self.__registrar_mensaje(mensaje=bot_men,
															recibido=False)

						elif contenidos[c]['tipo_dato'] == 'video':
							bot_men = self.__bot_interface.sendVideo(
															chat_id=chat,
															video=file_f,
															timeout=600
															)
							file_id = bot_men.video.file_id
							self.__registrar_mensaje(mensaje=bot_men,
																recibido=False)

						elif contenidos[c]['tipo_dato'] == 'nota_video':
							bot_men = self.__bot_interface.sendVideoNote(
															chat_id=chat,
															video_note=file_f,
															timeout=600
															)
							file_id = bot_men.video_note.file_id
							self.__registrar_mensaje(mensaje=bot_men,
																recibido=False)

						elif contenidos[c]['tipo_dato'] == 'audio':
							bot_men = self.__bot_interface.sendAudio(
															chat_id=chat,
															audio=file_f,
															timeout=600
															)
							file_id = bot_men.audio.file_id
							self.__registrar_mensaje(mensaje=bot_men,
																recibido=False)

						elif contenidos[c]['tipo_dato'] == 'nota_voz':
							bot_men = self.__bot_interface.sendVoice(
															chat_id=chat,
															voice=file_f,
															timeout=600
															)
							file_id = bot_men.voice.file_id
							self.__registrar_mensaje(mensaje=bot_men,
																recibido=False)


						elif contenidos[c]['tipo_dato'] == 'animacion':
							bot_men = self.__bot_interface.sendAnimation(
															chat_id=chat,
															animation=file_f,
															timeout=600
															)
							file_id = bot_men.animation.file_id
							self.__registrar_mensaje(mensaje=bot_men,
																recibido=False)

						elif contenidos[c]['tipo_dato'] == 'documento':
							bot_men = self.__bot_interface.sendDocument(
															chat_id=chat,
															document=file_f,
															timeout=1800
															)
							file_id = bot_men.document.file_id
							self.__registrar_mensaje(mensaje=bot_men,
																recibido=False)

						elif contenidos[c]['tipo_dato'] == 'sticker':
							bot_men = self.__bot_interface.sendSticker(
															chat_id=chat,
															sticker=file_f,
															timeout=60
															)
							file_id = bot_men.sticker.file_id
							self.__registrar_mensaje(mensaje=bot_men,
															recibido=False)

						#	Cerrar archivo si hubiera sido abierto del
						#	sistema de ficheros
						if hasattr(file_f, 'close'):
							#	Cerrar archivo
							file_f.close()

						#	Actualizar file_id
						if c is not None and file_id is not None and file_id != file_f:
							self.__bd_interface.editDatoMultimedia(
														id_dato=c,
														file_id=file_id)

				elif contenidos[c]['tipo_dato'] == 'contacto':
					for chat in id_chat:
						bot_men = self.__bot_interface.sendContact(
									chat_id=chat,
									phone_number=contenidos[c]['telefono'],
									first_name=contenidos[c]['nombre'],
									second_name=contenidos[c]['apellidos'],
									vcard=contenidos[c]['vcard'])
						self.__registrar_mensaje(mensaje=bot_men,
															recibido=False)

				elif contenidos[c]['tipo_dato'] == 'localizacion':

					for chat in id_chat:
						if ('titulo' not in contenidos[c] or
											not contenidos[c]['titulo']):
							bot_men = self.__bot_interface.sendLocation(
										chat_id=chat,
										latitude=contenidos[c]['latitud'],
										longitude=contenidos[c]['longitud'])
						else:
							bot_men = self.__bot_interface.sendVenue(
								chat_id=chat,
								latitude=contenidos[c]['latitud'],
								longitude=contenidos[c]['longitud'],
								title=contenidos[c]['titulo'],
								address=contenidos[c]['longitud'],
								foursquare_id=contenidos[c]['id_cuadrante']
								)

						self.__registrar_mensaje(mensaje=bot_men,
															recibido=False)

			except Exception as e:
				self.__log.error('Se ha producido un error en el envío del'\
								'siguiente contenido:\n{}\nDetalles '\
								'del error:\n{}'.format(contenidos[c], str(e)))
				continue

		self.__log.debug('Finalizada función "__send_contenido_into_messages" '\
															'de "BotServer"')

	def __install_directorio_base(self):

		"""Se ocupa de instalar el directorio base y prepaarlo
		"""

		self.__log.debug('Iniciada función "__install_directorio_base" de "BotServer"')

		#	Acceder al directorio base
		self.__log.info(('Accediendo al directorio base "%s"' %
											self.__config['directorio_base']))

		if os.path.isdir(self.__config['directorio_base']) == False:
			try:
				os.mkdir(self.__config['directorio_base'])
			except:
				raise ValueError(('No se puede crear el directorio %s' %
											self.__config['directorio_base']))

		#	Crear cada uno de los subdirectorios
		subdir_list = ['imagenes', 'documentos', 'videos', 'audios', 'notas_voz',
						'notas_video', 'stickers', 'conversaciones_recopiladas',
						'animaciones']

		for subdir in subdir_list:
			self.__log.info(('Accediendo al directorio "%s"' %
								self.__config['directorio_base']+subdir+'/'))

			if not os.path.isdir(self.__config['directorio_base']+subdir+'/'):
				try:
					os.mkdir(self.__config['directorio_base']+subdir+'/')
				except:
					raise ValueError(('No se puede crear el directorio %s' %
								self.__config['directorio_base']+subdir+'/'))

		self.__log.debug('Finalizada función "__install_directorio_base" '\
															'de "BotServer"')

	def __error_handler(self, bot, update, error):
		self.__log.error(error)	# Se imprime una entrada de log de error

	### Métodos estáticos públicos ###

	def get_config_file_template():

		"""
		Permite obtener un objeto JSON con una plantilla del fichero
			de configuración
		"""
		return json.dumps(BotServer.__CONFIG_FILE_TEMP, indent=2)

	def save_config_file_template(filename: str):

		"""
		Permite almacenar un objeto JSON con una plantilla del fichero
			de configuración en un fichero de configuración
		"""
		with open(filename,'w') as config_file_temp:
			config_file_temp.write( json.dumps(BotServer.__CONFIG_FILE_TEMP,
												indent=2) )

	### Métodos públicos ###
	def start(self):

		"""Inicia el funcionamiento completo del sistema.
			Para deternerlo, será necesario mandar al proceso una señal de
			terminación
		"""

		#	Establecer el directorio base
		self.__install_directorio_base()


		#	Conectar con la base de datos e iniciar la interfaz de acceso
		self.__bd_interface = BotServerDAO(
					self.__config['directorio_base']+'cprofessorbot_BD.db',
					debug=self.__debug_mode)

		#	Iniciar el administrador de preguntas
		self.__quest_manager = QuestionManager(self.__bd_interface,
											self.__config['directorio_base'])

		self.__log.info('Cargando preguntas y respuestas en la base de datos:')
		self.__quest_manager.removeAllConcepts()

		if not isinstance(self.__config['fuentes_conceptos'], list):
			self.__config['fuentes_conceptos'] = [
											self.__config['fuentes_conceptos']
										]

		#	Si no hay ninguna fuente de conceptos teóricos, se manda un aviso
		if not self.__config['fuentes_conceptos']:
			self.__log.warning('No se ha especificado ningún fichero JSON o '\
							'direccion URL como fuentes de Conceptos Teóricos')

		for fuente in self.__config['fuentes_conceptos']:

			if not fuente:
				continue

			elif fuente.startswith('http'):
				#	Cargar de url
				self.__log.info('Leyendo conceptos teóricos del '\
												'sitio web: {}'.format(fuente))

				extr = self.__quest_manager.load_from_url(fuente)

				#	Almacenar los conceptos extraídos en un fichero JSON
				extr_filename = (self.__config['directorio_base']+
							'/concepto_web%d.json' %
							self.__config['fuentes_conceptos'].index(fuente))

				with open(extr_filename, 'w') as f:
					f.write(json.dumps(extr, indent=2))

				self.__log.info('Se han almacenado los conceptos teóricos'\
								' de "{}" en el fichero JSON "{}"'.format(
													fuente, extr_filename))

			else:
				#	Cargar de fichero
				self.__log.info(('Leyendo conceptos teóricos del fichero: "%s"'%
																		fuente))
				try:
					self.__quest_manager.load_from_file(fuente)
				except Exception as e:
					self.__log.error('Se produjo el siguiente error'\
						' al tratar de abrir "{}":\n{}'.format(fuente, str(e)))
					continue

		#	Iniciar el analizador de discurso
		self.__log.info('Entrenando analizador de discurso')
		self.__speech_handler = SpeechHandler()

		#	Entrenar el analizador con la lista de palabras
		#	recogidas y los nombres
		with open(os.path.dirname(__file__)+'/palabras_validas.txt', 'r') as f:
			self.__speech_handler.fit(f)

		with open(os.path.dirname(__file__)+'/lista_nombres.txt', 'r') as f:
			self.__speech_handler.fit(f)

		#	Entrenar el analizador con los conceptos y las respuestas de texto
		lista_conceptos = self.__bd_interface.listAllConcepts()

		if lista_conceptos:
			self.__speech_handler.fit(lista_conceptos)

		del lista_conceptos

		lista_respuestas = self.__bd_interface.listAllConceptsTextAnswers()

		if lista_respuestas:
			self.__speech_handler.fit(lista_respuestas)

		del lista_respuestas

		#	Inicializar la interfaz del bot
		self.__log.info('Iniciando Actualizadores, Despachadores y Manejadores'\
							' de Eventos')
		try:
			self.__bot_interface, self.__bot_updater = self.__initialize_interface()
		except telegram.error.InvalidToken:
			raise ValueError('Tóken introducido no válido')
		except:
			raise

		# Arrancar el funcionamiento de la interfaz
		self.__bot_updater.start_polling()

		self.__log.info('Sistema iniciado')

		#	A partir de ahora se escribe en el fichero de log
		self.__log.propagate = False
		self.__log.addHandler( logging.FileHandler(
					self.__config['directorio_base']+'server_log.txt', 'a'))
		self.__log.handlers[0].setFormatter(
							logging.Formatter(
								fmt='%(levelname)s - %(asctime)s - %(message)s',
								datefmt='%d-%b-%y %H:%M:%S'))

		# Fijar la ejecución del sistema
		self.__bot_updater.idle()


# https://realpython.com/documenting-python-code/
# pip3 install python-telegram-bot --upgrade
# sudo apt-get install sqlite3
# pip3 install requests

# Página oficial de sqlite3
#https://www.sqlite.org/index.html

# Página de realpython.com con documentación básica sobre el uso del módulo requests
# https://realpython.com/python-requests/ (última visita: 20 de Julio)
