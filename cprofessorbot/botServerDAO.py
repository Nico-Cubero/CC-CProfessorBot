# -*- coding: utf-8 -*-
################################################################################
# Descripción: Módulo que contiene la definición e implementación de la clase
#				BotServerDAO
# Autor: Nicolás Cubero Torres
################################################################################

#	Módulos importados
import logging
import sqlite3
import datetime
import os.path
import telegram
from threading import Lock
from collections import OrderedDict
from cprofessorbot.nlu import compare_words

#	Definición e implementación de la clase BotServerDAO
class BotServerDAO:

	"""
	Interfaz de acceso a la base de datos usada por el sistema C-ProfessorBot

	Atributos
	-----------
	bd_file : str
		Ruta del fichero donde se ubica la base de datos local usada por
		este sistema
	debug: bool
		Iniciar el modo de depuración o no

	"""

	### Definición de constantes ###
	__BD_TIPOS = {
					'TIPO_USUARIO': {
										'alumno': 0,
										'docente': 1
									},
					'TIPO_FORO': {
										'group': 0,
										'supergroup': 1
								},
					'TIPO_EVENTO_CHAT_GRUPAL': {
													'entrada': 0,
													'salida': 1,
													'registro': 2,
													'ban': 3,
													'readmision': 4,
													'expulsion': 5
											},
					'TIPO_DATOARCHIVO': {
												'imagen': 0,
												'video': 1,
												'audio': 2,
												'nota_voz': 3,
												'nota_video': 4,
												'animacion': 5,
												'documento': 6,
												'sticker': 7
										},
					'TIPO_STICKER': {
										'normal': 0,
										'animado': 1
								}
				}


	def __install_database(filename_output: str,
				src_code_db=os.path.dirname(__file__)+'/CProfessorBot_BD.sql'):

		#	Se crea una conexión a la base de datos a crear y sobre
		#	la misma se ejecuta el script de creación del esquema
		con = sqlite3.connect(filename_output)

		#	El script de creación se toma del fichero
		with open(src_code_db, 'r') as f:
			con.executescript(f.read())

		con.commit()
		con.close()

	def __init__(self, bd_file: str, debug: bool=False):

		"""
		Parámetros:
		--------------

		bd_file : str
			Ruta del fichero donde se ubica la base de datos local usada por
			este sistema

		debug: bool
			Iniciar el modo de depuración o no
		"""

		self.__bd_file = bd_file
		self.__con_bd = None

		#	Configurar el logging del sistema
		self.__log = logging.getLogger('cprofessorbot_log')

		#	Comprobar que la base de datos existe
		if os.path.isfile(bd_file) == False:
			BotServerDAO.__install_database(filename_output=bd_file)

		#	Registrar adaptadores de objetos Python a objetos admitdos en SQLite
		#	Tipo bool
		sqlite3.register_adapter(bool, BotServerDAO.__bool_adapter)

		#	Tipo datetime
		sqlite3.register_adapter(datetime.datetime,
												BotServerDAO.__datetime_adapter)

		#	cualquier tipo inventado
		#sqlite3.register_adapter(str, BotServerDAO.__bool_adapter)

		#	Registrar conversores de tipos de datos de SQLite3 a objetos Python
		#	Tipo bool
		sqlite3.register_converter('BOOLEAN', BotServerDAO.__boolean_converter)

		#	Tipo date
		sqlite3.register_converter('DATE', BotServerDAO.__datetime_converter)

		#	Tipo Usuario
		sqlite3.register_converter('TIPO_USUARIO',
										BotServerDAO.__tipo_usuario_converter)

		#	Tipo Foro
		sqlite3.register_converter('TIPO_FORO',
										BotServerDAO.__tipo_foro_converter)

		#	Tipo Dato Multimedia
		sqlite3.register_converter('TIPO_DATOARCHIVO',
								BotServerDAO.__tipo_datoarchivo_converter)

		#	Tipo Evento Chat Grupal
		sqlite3.register_converter('TIPO_EVENTO_CHAT_GRUPAL',
							BotServerDAO.__tipo_evento_chat_grupal_converter)

		#	Tipo Sticker
		sqlite3.register_converter('TIPO_STICKER',
										BotServerDAO.__tipo_sticker_converter)

		#	Conectar con la base de datos
		self.__con_bd = sqlite3.connect(bd_file,
							check_same_thread=False,
							detect_types=
								sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

		#	Establecer el tipo de dato usado para representar tuplas
		self.__con_bd.row_factory = sqlite3.Row

		#	Registrar función compare_words
		self.__con_bd.create_function('compare_words', 2, compare_words)

		#	Activar modo de depuración

		if debug:
			self.__con_bd.execute('PRAGMA foreign_keys = true;')
			self.__con_bd.execute('PRAGMA foreign_keys_check = 1;')
			self.__con_bd.execute('PRAGMA integrity_check = 1;')
			self.__con_bd.set_trace_callback(self.__log.debug)
		else:
			self.__con_bd.execute('PRAGMA foreign_keys = false;')
			self.__con_bd.execute('PRAGMA foreign_keys_check = 0;')
			self.__con_bd.execute('PRAGMA integrity_check = 0;')

	### Conversores y adaptadores de tipos de datos ###

	def __bool_adapter(bool_value):

		if not isinstance(bool_value, bool):
			raise ValueError('Bool value debe ser passed')

		return int(bool_value)

	def __datetime_adapter(time_value):

		if not isinstance(time_value, datetime.datetime):
			raise ValueError('"time_value" no es un objeto datetime.datetime '\
								'válido')

		return time_value.timestamp()

	def __tipo_adapter(string_value):

		if not isinstance(string_value, str):
			raise ValueError('A str object debe ser proporcionado')

		for tipo in BotServerDAO.__BD_TIPOS:

			#	Buscar el valor numérico asociado al valor pasado y devolverlo
			if string_value in BotServerDAO.__BD_TIPOS[tipo]:
				return BotServerDAO.__BD_TIPOS[tipo][string_value]

		raise ValueError('Valor desconocido: "%s"' % string_value)

	def __boolean_converter(int_value):
		return bool(int(int_value))

	def __datetime_converter(float_value):

		float_value = float(float_value)
		return datetime.datetime.fromtimestamp(float_value)

	def __tipo_usuario_converter(int_value):

		if int_value is None:
			return None
		else:
			try:
				int_value = int(int_value)
			except:
				#	Convertir de array de bytes a string si es necesario
				return int_value.decode('utf-8') if hasattr(int_value,
														'decode') else int_value

		for tipo in BotServerDAO.__BD_TIPOS['TIPO_USUARIO']:

			#	Devolver la clave cuyo valor sea el pasado como argumento
			if BotServerDAO.__BD_TIPOS['TIPO_USUARIO'][tipo] == int_value:
				return tipo

		raise ValueError('"%d" not a valid value' % int_value)

	def __tipo_foro_converter(int_value):

		if not int_value:
			return None
		else:
			try:
				int_value = int(int_value)
			except:
				#	Convertir de array de bytes a string
				return int_value.decode('utf-8') if hasattr(int_value,
														'decode') else int_value

		for tipo in BotServerDAO.__BD_TIPOS['TIPO_FORO']:

			#	Devolver la clave cuyo valor sea el pasado como argumento
			if BotServerDAO.__BD_TIPOS['TIPO_FORO'][tipo] == int_value:
				return tipo

		raise ValueError('"%d" not a valid value' % int_value)

	def __tipo_evento_chat_grupal_converter(int_value):

		if not int_value:
			return None
		else:
			try:
				int_value = int(int_value)
			except:
				#	Convertir de array de bytes a string
				return int_value.decode('utf-8') if hasattr(int_value,
														'decode') else int_value

		for tipo in BotServerDAO.__BD_TIPOS['TIPO_EVENTO_CHAT_GRUPAL']:

			#	Devolver la clave cuyo valor sea el pasado como argumento
			if (BotServerDAO.__BD_TIPOS['TIPO_EVENTO_CHAT_GRUPAL']
														[tipo] == int_value):
				return tipo

		raise ValueError('"%d" not a valid value' % int_value)

	def __tipo_datoarchivo_converter(int_value):

		if not int_value:
			return None
		else:
			try:
				int_value = int(int_value)
			except:
				#	Convertir de array de bytes a string
				return int_value.decode('utf-8') if hasattr(int_value,
														'decode') else int_value

		for tipo in BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO']:

			#	Devolver la clave cuyo valor sea el pasado como argumento
			if BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO'][tipo] == int_value:
				return tipo

		raise ValueError('"%d" not a valid value' % int_value)

	def __tipo_sticker_converter(int_value):

		if not int_value:
			return None
		else:
			try:
				int_value = int(int_value)
			except:
				#	Convertir de array de bytes a string
				return int_value.decode('utf-8') if hasattr(int_value,
													'decode') else int_value

		for tipo in BotServerDAO.__BD_TIPOS['TIPO_STICKER']:

			#	Devolver la clave cuyo valor sea el pasado como argumento
			if BotServerDAO.__BD_TIPOS['TIPO_STICKER'][tipo] == int_value:
				return tipo

		raise ValueError('"%d" not a valid value' % int_value)


	def __to_sql_tuple(tup):

		if not tup:
			return None

		#	Objeto a devolver
		ret = list(tup)

		#	Formatear cada elemento de la tupla Python para convertirlo en
		#	tupla admitida por SQL
		for i in range(len(ret)):

			if isinstance(ret[i], (tuple, list, sqlite3.Row)):
				#	De las tuplas y listas se toma el valor que contienen
				ret[i] = ret[i][0]

			if isinstance(ret[i], str):
				#	Para cadenas, es necesario rodear cada elemento
				#	entre comillas
				ret[i] = '"'+ret[i]+'"'
			else:
				#	Se convierte en cadena simplemente
				ret[i] = str(ret[i])

		#	Devolver tupla SQL
		return '('+','.join(ret)+')'

	### Interfaz de la clase ###

	def getUsuario(self, user_id: int):

		"""
		Permite obtener al usuario de la base de datos cuyo "id" de usuario
			coincida con el que se ha pasado como argumento.

		Argumentos:
		-----------
			user_id: "Id" del usuario por el cual se buscará en la base de datos

		Devuelve:
			dict: Diccionario con los siguientes campos:
				- telegram_user: (telegram.User) Usuario telegram con los datos
					del usuario
				- id_chat: (int) Id del chat del usuario
				- fecha_registro: (datetime.datetime) Fecha de registro del
									usuario
				- tipo: (str) "usuario_docente" o "usuario_alumno"
				- valido: (bool) Usuario válido (True) o no (False)
		"""

		self.__log.debug('Ejecutada función "getUsuario" de "BotServerDAO"')

		#	Comprobar parámetros de entrada
		if not isinstance(user_id, int):
			raise ValueError('"user_id" debe ser int')

		#	Tomar el cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar la consulta
		self.__log.debug('Realizando consulta con campo id=%d' % user_id)

		mutex.acquire()
		cursor.execute('SELECT * FROM Usuario WHERE id=?',(user_id,))

		#	Tomar los datos de la consulta
		datos = cursor.fetchone()

		#	Cerrar el cursor y semáforo
		cursor.close()
		mutex.release()

		if datos == None:
			self.__log.debug('No encontrado usuario id=%d' % user_id)
			self.__log.debug('Finaliza la ejecución de la función "getUsuario"'\
														' de "BotServerDAO"')
			return None
		else:
			self.__log.debug('Encontrado usuario id=%d' % user_id)

			usuario = {}

			usuario['telegram_user'] = telegram.User(id=datos[0],
													first_name=datos[1],
													is_bot=False,
													last_name=datos[2],
													username=datos[3]
										)

			usuario['id_chat'] = datos[4]
			usuario['fecha_registro'] = datos[5]
			usuario['tipo'] = datos[6]
			usuario['valido'] = datos[7]

			self.__log.debug('Finaliza la ejecución de la función'\
											' "getUsuario" de "BotServerDAO"')
			return usuario

	def existsUsuario(self, user_id: int):

		"""
		Permite determinar si existe un usuario de la base de datos cuyo "id"
			de usuario coincida con el que se ha pasado como argumento.

		Argumentos:
		-----------
			user_id: "Id" del usuario por el cual se buscará en la base de datos

		Devuelve:
			bool: True si existe o False en caso contrario
		"""

		self.__log.debug('Ejecutada función "existsUsuario" de "BotServerDAO"')

		#	Comprobar parámetros de entrada
		if not isinstance(user_id, int):
			raise ValueError('"user_id" debe ser int')

		#	Preparar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar la consulta
		self.__log.debug('Realizando consulta con campo id=%d' % user_id)
		mutex.acquire()
		cursor.execute('SELECT * FROM Usuario WHERE id=?',(user_id,))

		#	Tomar los datos de la consulta
		datos = cursor.fetchone()

		#	Cerrar el cursor y semáforo
		cursor.close()
		mutex.release()

		if datos == None:
			self.__log.debug('No encontrado usuario id=%d' % user_id)
			self.__log.debug('Finaliza la ejecución de la función'\
									' "existsUsuario" de "BotServerDAO"')
			return False
		else:
			self.__log.debug('Encontrado usuario id=%d' % user_id)
			self.__log.debug('Finaliza la ejecución de la función'\
										' "existsUsuario" de "BotServerDAO"')
			return True


	def addUsuario(self, id_usuario: int, nombre: str, apellidos: str,
					username: str, id_chat: int,
					fecha_registro: datetime.datetime, tipo: str,
					valido=True):

		"""Permite registrar un nuevo usuario en la base de datos:

		Parámetros:
		-----------
		id_usuario: int
			Identificador asociado al usuario asociado por Telegram

		nombre: str
			Primer nombre del usuario

		apellidos: str
			Segundo nombre o apellidos del usuario

		username: str
			Nombre de usuario asociado al Usuario en la plataforma
			de mensajerı́a.

		id chat: int
			Identificador asociado al canal de chat privado de un Usuario

		fecha registro: datetime.datetime
			Fecha en la que el Usuario fue registrado en su tipo actual.

		tipo: str
			Tipo de usuario: 'docente' o 'alumno'

		valido: bool
			Indica si el usuario es válido o no. Por defecto True
		"""

		self.__log.debug('Ejecutada función "addUsuario" de "BotServerDAO"')

		#	Se toma un cursor para insertar datos y se prepara el semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Comprobar los datos de entrada
		if not isinstance(nombre, str):
			raise ValueError('"nombre" debe ser str')

		if apellidos:

			if not isinstance(apellidos, str):
				raise ValueError('"apellidos" debe ser str')

		if username:

			if not isinstance(username, str):
				raise ValueError('"username" debe ser str')


		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe ser int')

		if not isinstance(fecha_registro, datetime.datetime):
			raise ValueError('"fecha_registro" debe ser un objeto de tipo'\
														' datetime.datetime')

		if not isinstance(tipo, str):
			raise ValueError('"tipo" debe ser str')
		else:
			tipo = BotServerDAO.__BD_TIPOS['TIPO_USUARIO'][tipo]

		if not isinstance(valido, bool):
			raise ValueError('"valido" debe ser bool')

		#	Se intentan insertar los datos en la tabla
		datos = (id_usuario, nombre, apellidos, username, id_chat,
														fecha_registro, tipo,
														valido)
		self.__log.debug('Insertando los siguientes datos:'\
						' id_usuario={}, nombre={}, apellidos={},'\
						' username={}, id_chat={}, fecha_registro={}, tipo={},'\
						' valido={}'.format(*datos))

		mutex.acquire()
		insercion = cursor.execute(
								'INSERT INTO Usuario VALUES(?,?,?,?,?,?,?,?);',
																		datos)

		#	Realiza commit
		self.__con_bd.commit()

		#	Cierre del cursor y liberación del semáforo
		mutex.release()
		cursor.close()

		self.__log.debug('Inserción realizada con éxito, fin de ejecución '\
								'de la función "addUsuario" de "BotServerDAO"')



	def editUsuario(self, id_usuario: int, nombre=None, apellidos=None,
					username=None, id_chat=None, fecha_registro=None,
					tipo=None, valido=None):

		"""Permite editar los datos de un usuario. Se debe de proporcionar
			únicamente los parámetros cuyos valores se desean editar

		Parámetros:
		----------
		id_usuario: int
			Identificador asociado al usuario asociado por Telegram

		nombre: str
			Primer nombre del usuario

		apellidos: str
			Segundo nombre o apellidos del usuario

		username: str
			Nombre de usuario asociado al Usuario en la plataforma
			de mensajerı́a.

		id chat: int
			Identificador asociado al canal de chat privado de un Usuario

		fecha registro: datetime.datetime
				Fecha en la que el Usuario fue registrado en su tipo actual.

		tipo: str
			Tipo de usuario: 'docente' o 'alumno'

		valido: bool
			Indica si el usuario es válido o no. Por defecto True
		"""

		self.__log.debug('Ejecutada función "editUsuario" de "BotServerDAO"')

		#	Tomar un cursor para editar datos y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Se va a construir la consulta en función de los datos proporcionados
		datos = []
		campos = ''

		if nombre:

			if not isinstance(nombre, str):
				raise ValueError('"nombre" debe ser str')

			datos.append(nombre)
			campos += 'nombre=?,'

		if apellidos:

			if not isinstance(apellidos, str):
				raise ValueError('"apellidos" debe ser str')

			datos.append(apellidos)
			campos += 'apellidos=?,'

		if username:

			if not isinstance(username, str):
				raise ValueError('"username" debe ser str')

			datos.append(username)
			campos += 'username=?,'

		if id_chat is not None:

			if not isinstance(id_chat, int):
				raise ValueError('"id_chat" debe ser int')

			datos.append(id_chat)
			campos += 'id_chat=?,'

		if fecha_registro:

			if not isinstance(fecha_registro, datetime.datetime):
				raise ValueError('"fecha_registro" debe ser un objeto de'\
								' tipo datetime.datetime')

			datos.append(fecha_registro)
			campos += 'fecha_registro=?,'

		if tipo:

			if not isinstance(tipo, str):
				raise ValueError('"tipo" debe ser str')

			tipo = BotServerDAO.__BD_TIPOS['TIPO_USUARIO'][tipo]

			datos.append(tipo)
			campos  +=  'tipo=?,'

		if valido is not None:

			if not isinstance(valido, bool):
				raise ValueError('"valido" debe ser bool')

			datos.append(valido)
			campos += 'valido=?,'

		if datos:
			campos = campos[:-1]	#	Borrar coma sobrante
			datos.append(id_usuario)		#	Añadir al usuario
		else:
			#	No se ha especificaado ningún campo a modificar
			raise ValueError('Se debe de proporcionar al menos un parámetro')

		#	Se ejecuta la actualización
		self.__log.debug('Se ejecuta la sentencia de actualización'\
						' con datos: id_usuario={}, nombre={}, apellidos={},'\
						' username={}, id_chat={}, fecha_registro={}, tipo={},'\
						' valido={}'.format(id_usuario, nombre, apellidos,
						username, id_chat, fecha_registro, tipo, valido))
		mutex.acquire()

		cursor.execute(('UPDATE Usuario SET %s WHERE id=?' %
													campos), tuple(datos))

		self.__con_bd.commit()	#	Realiza el commit

		#	Cerrar cursor y semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Actualización realizada con éxito, fin de ejecución'\
							' de la función "editUsuario" de "BotServerDAO"')

	def getForo(self, foro_id: int):

		"""
		Permite obtener el foro docente de la base de datos cuyo "id" de foro
			coincida con el que se ha pasado como argumento.

		Argumentos:
		-----------
			foro_id: "Id" del foro por el cual se buscará en la base de datos

		Devuelve:
			dict: Diccionario con los siguientes campos:
				- id: id asignado al chat del foro
				- nombre: Nombre asignado al grupo docente
				- tipo: (str) "usuario_docente" o "usuario_alumno"
				- valido: True: Si el foro es reconocido como un foro válido
					(el asistente es administrador en el grupo o supergrupo),
					False en caso contrario
		"""

		self.__log.debug('Ejecutada función "getForo" de "BotServerDAO"')

		#	Comprobar datos de entrada
		if not isinstance(foro_id, int):
			raise ValueError('"foro_id" debe ser int')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar la consulta
		self.__log.debug('Realizando consulta con campo id_chat=%d' % foro_id)
		mutex.acquire()
		cursor.execute('SELECT * FROM Foro WHERE id_chat=?',(foro_id,))

		#	Tomar los datos de la consulta
		datos = cursor.fetchone()

		#	Cerrar el cursor y semáforo
		cursor.close()
		mutex.release()

		if not datos:
			self.__log.debug('No encontrado foro id=%d' % foro_id)
			self.__log.debug('Finaliza la ejecución de la función "getForo" de'
															' "BotServerDAO"')
			return None
		else:
			self.__log.debug('Encontrado Foro id=%d' % foro_id)

			foro = {}

			foro['id'] = datos[0]
			foro['nombre'] = datos[1]
			foro['tipo'] = datos[2] #'group' if datos[2] == 0 else 'supergroup'
			foro['valido'] = datos[3] #bool(datos[3])

			self.__log.debug('Finaliza la ejecución de la función "getForo" de'\
															' "BotServerDAO"')
			return foro


	def addForo(self, id_chat: int, nombre: str,
				tipo: str, valido: bool, fecha_creacion: datetime.datetime):

		"""
		Permite añadir un nuevo foro a la base de datos

		Atributos:
		----------
			id_chat: (int) Identificador de chat asignado univocamente al grupo
						o supergrupo asociado al foro
			nombre: (str) Nombre del grupo o supergrupo asignado al foro docente
			tipo: (str) "group" si el foro lleva asociado un grupo o
				"supergroup" si lleva asociado un foro
			valido: (bool) True si el foro es válido (el asistente es usuario
					administrador en dicho foro) o False en caso contrario
		"""

		self.__log.debug('Ejecutada función "addForo" de "BotServerDAO"')

		#	Comprobar que los datos sean válidos
		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe de ser int')

		if not isinstance(nombre, str):
			raise ValueError('"nombre" debe de ser str')

		if not isinstance(tipo, str):
			raise ValueError('"tipo" debe de ser str')
		else:
			tipo = BotServerDAO.__BD_TIPOS['TIPO_FORO'][tipo]

		if not isinstance(valido, bool):
			raise ValueError('"valido" debe de ser bool')

		if not isinstance(fecha_creacion, datetime.datetime):
			raise ValueError('"fecha_creacion" debe de ser datetime.datetime')

		#	Se toma un cursor para insertar datos y se prepara el semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Se intentan insertar los datos en la tabla
		datos = (id_chat, nombre, tipo, valido, fecha_creacion)
		self.__log.debug('Insertando los siguientes datos en la tabla'\
						' Foro: id_chat={}, nombre={}, tipo={}, valido={},'\
						' fecha_creacion={}'.format(*datos))

		mutex.acquire()
		insercion = cursor.execute('INSERT INTO Foro VALUES(?,?,?,?,?);', datos)

		#	Realiza commit
		self.__con_bd.commit()

		#	Cerrar cursor y semáforo
		cursor.close()
		mutex.release()


	def editForo(self, id_chat: int, nombre=None, tipo=None,
								valido=None,
								fecha_creacion: datetime.datetime=None):

		"""Permite editar los datos de un Foro existente. Únicamente se deben
			de proporcionar los parámetros de los valores que se desean editar
			y el "id_chat" del foro que se desea editar:

			Parámetros:
			-----------
			id_chat: (int) Identificador de chat asignado univocamente al grupo
						o supergrupo asociado al foro
			nombre: (str) Nombre del grupo o supergrupo asignado al foro docente
			tipo: (str) "grupo" si el foro lleva asociado un grupo o
				"supergrupo" si lleva asociado un supergrupo
			valido: (bool) True si el foro es válido (el asistente es usuario
					administrador en dicho foro) o False en caso contrario

		"""

		self.__log.debug('Ejecutada función "editForo" de "BotServerDAO"')

		#	Se toma un cursor para editar datos y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Se va a construir la consulta en función de los datos proporcionados
		datos = []
		campos = ''

		if nombre:
			if not isinstance(nombre, str):
				raise ValueError('"nombre" debe ser str')

			datos.append(nombre)
			campos += 'nombre=?,'

		if tipo:

			if not isinstance(tipo, str) and tipo not in ('grupo','supergrupo'):
				raise ValueError('"tipo" debe ser str y debe de adoptar los'\
											' valores "grupo" y "supergrupo"')


			datos.append(tipo)
			campos += 'tipo=?,'

		if valido is not None:

			if not isinstance(valido, bool):
				raise ValueError('"valido" debe ser bool')

			datos.append(int(valido))
			campos += 'valido=?,'

		if fecha_creacion:

			if not isinstance(fecha_creacion, datetime.datetime):
				raise valueError('"fecha_creacion" no es datetime.datetime')

			datos.append(fecha_creacion)
			campos += 'fecha_creacion=?,'

		if datos:
			campos = campos[:-1]	#	Borrar coma sobrante
			datos.append(id_chat)	#	Añadir al usuario
		else:
			#	No se ha especificaado ningún campo a modificar
			raise ValueError('Se debe de proporcionar al menos un parámetro')

		#	Se ejecuta la actualización
		self.__log.debug('Se ejecuta la sentencia de actualización con datos:'\
						' id_chat={}, nombre={}, tipo={}, valido={},'\
						' fecha_creacion={}'.format(id_chat, nombre, tipo,
													valido, fecha_creacion))
		mutex.acquire()
		actualizacion = cursor.execute('UPDATE Foro SET %s WHERE'\
										' id_chat=?' % (campos), tuple(datos))

		#	Realizar el commit
		self.__con_bd.commit()

		#	Cerrar cursor y semáforo
		cursor.close()
		mutex.release()

		return actualizacion

	def removeForo(self, id_chat: int):

		"""Permite eliminar un Foro de la base de datos

		Parámetros:
		-----------
		id_chat: int
			Identificador del foro que se desea eliminar

		"""
		self.__log.debug('Ejecutada función "removeForo" de "BotServerDAO"')

		#	Comprobar que los datos proporcionados sean válidos y prepararlos
		if type(id_chat) != int:
			raise ValueError('"id_chat" debe ser int')

		#	Se toma un cursor para eliminar datos y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Se ejecuta el borrado
		self.__log.debug('Se ejecuta la sentencia de borrado con datos'\
							' id_chat=%d' % id_chat)
		mutex.acquire()
		cursor.execute('DELETE FROM Foro WHERE id_chat=?;', (id_chat,))

		#	Realizar el commit
		self.__con_bd.commit()

		#	Cerrar el cursor y el semáforo
		cursor.close()
		mutex.release()

	def listForos(self, solo_validos=True):

		"""Permite listar todos los foros almacenados

		Argumentos:
		-----------
		solo_validos: bool
			Establece si en el listado sólo deben de aparecer los foros válidos
			(True) o todos (False)

		Devuelve:
		---------
		dict: Que consta del par id (int) - foro (dict)
			"foro" es a su vez un diccionario con los siguientes datos:
			- nombre: str
				Nombre o tı́tulo de grupo asociado al Foro.
			- tipo: str
				Tipo de chat grupal asociado al Foro y que puede ser:
				grupo o supergrupo.
			- fecha_registro: datetime.datetime
				Fecha en la que el foro fue registrado en el sistema en
				su tipo actual
			- valido: bool
				Indica si el foro es válido (True) o no (False)
		"""

		self.__log.debug('Ejecutada función "listForos" de "BotServerDAO"')

		#	Obtener cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()
		filtro = 'WHERE valido=1' if solo_validos else ''

		datos = {}

		#	Realizar la consulta
		mutex.acquire()
		for fila in cursor.execute('SELECT * FROM Foro %s;' % filtro):

			#self.__log.debug('Encontrado Foro id=%d' % fila[0])

			foro = {}

			foro['nombre'] = fila[1]
			foro['tipo'] = fila[2] #'group' if fila[2] == 0 else 'supergroup'
			foro['valido'] = fila[3]
			foro['fecha_creacion'] = fila[4]

			#	Añadir el foro encontrado
			datos[fila[0]] = foro

		#	Cerrar el cursor y semáforo
		cursor.close()
		mutex.release()

		if not datos:
			self.__log.debug('No se ha encontrado ningún foro docente')
			datos = None
		else:
			self.__log.debug('Se ha encontrado %d foros', len(datos))

		self.__log.debug('Finalizada función "listForos" de "BotServerDAO"')

		return datos

	def getUsuario_status_Foro(self, id_chat: int, id_usuario: int):

		"""Permite obtener información sobre el estado en un
			determinado Foro

			Parámetros:
			-----------
			id_chat: int
				Identificador de chat asociado al chat grupal del foro docente

			id_usuario: int
				Identificador asociado al usuario

			Devuelve:
			---------
				dict: Con los siguientes campos:
					- ban: bool
						Indica si el usuario está baneado o no

					- n_avisos: int
						Indica el número de avisos que lleva acumulado el
						usuario por el envío de mensajes no pertenecientes al
						ámbito académico
		"""

		self.__log.debug('Ejecutada función "getUsuario_status_Foro" de'\
							' "BotServerDAO"')

		#	Se comprueban que los datos sean válidos
		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe de ser int')

		if not isinstance(id_usuario, int):
			raise ValueError('"id_usuario" debe de ser int')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar la consulta
		self.__log.debug('Realizando consulta con campo id_chat=%d e '\
									'id_usuario=%d' % (id_chat, id_usuario))
		mutex.acquire()
		cursor.execute('''SELECT ban, n_avisos
							FROM Foro_Usuario
							WHERE id_chat_foro=? AND id_usuario=?''',
							(id_chat, id_usuario))

		#	Tomar los datos de la consulta
		datos = cursor.fetchone()

		#	Cerrar el cursor y semáforo
		cursor.close()
		mutex.release()

		if datos == None:
			self.__log.debug('No encontrado al usuario con id=%d en el foro'\
										' con id=%d' % (id_chat, id_usuario))
			self.__log.debug('Finaliza la ejecución de la función '\
								'"getUsuario_status_Foro" de "BotServerDAO"')
			status = None
		else:
			self.__log.debug('Encontrado al usuario con id=%d en el foro'\
										' con id=%d' % (id_chat, id_usuario))
			status = {
						'ban': bool(datos[0]),
						'n_avisos': datos[1]
					}


			self.__log.debug('Finaliza la ejecución de la función '\
								'"getUsuario_status_Foro" de "BotServerDAO"')

		return status

	def listUsuarios_in_Foro(self, id_chat: int, solo_alumnos=False,
															solo_valido=True):

		"""Permite obtener información sobre todos los usuarios presentes en un
			foro además de información sobre su status

		Parámetros:
		-----------

			id_chat: int
				Identificador de chat asociado al chat grupal del foro docente

			solo_alumnos: bool
				Indica si sólo se desean listar los alumnos (True) o también
				los docentes

		Devuelve:
		---------
			dict: Formado por el par id_usuario (int) - datos (dict)
				Por su parte, los datos incluídos en el diccionario
				presentan los siguientes campos:
				- id_usuario: int
					Identificador asociado al usuario asociado por Telegram

				- nombre: str
					Primer nombre del usuario

				- apellidos: str
					Segundo nombre o apellidos del usuario

				- username: str
					Nombre de usuario asociado al Usuario en la plataforma
					de mensajerı́a.

				- telegram_user: Telegram.user
					Usuario Telegram con los datos del usuario

				- id chat: int
					Identificador asociado al canal de chat privado
						de un Usuario

				- fecha registro: datetime.datetime
						Fecha en la que el Usuario fue registrado en
						su tipo actual.

				- ban: bool
					Indica si el usuario está baneado o no

				- n_avisos: int
					Indica el número de avisos que lleva acumulado el
					usuario por el envío de mensajes no pertenecientes al
					ámbito académico
		"""

		self.__log.debug('Ejecutada función "listUsuarios_in_Foro" '\
							'de "BotServerDAO"')

		#	Se comprueban que los datos sean válidos
		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe de ser int')

		#	Tomar el cursor y el semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Preparar la consulta
		filtro_valido = 'Usuario.valido=1' if solo_valido else ''
		filtro_alumnos = 'Usuario.tipo=0' if solo_alumnos else ''
		nexo1 = 'AND' if solo_valido and solo_alumnos else ''
		nexo2 = 'AND' if solo_valido or solo_alumnos else ''

		#	Realizar la consulta
		self.__log.debug('Realizando consulta con campo id_chat=%d' % id_chat)
		mutex.acquire()

		consulta = cursor.execute(
					'''SELECT Usuario.id, Usuario.nombre, Usuario.apellidos,
							Usuario.username, Usuario.id_chat,
							Usuario.fecha_registro, Usuario.tipo, Usuario.valido,
							Foro_Usuario.ban, Foro_Usuario.n_avisos
						FROM Usuario, Foro_Usuario
						WHERE %s %s %s %s Usuario.id = Foro_Usuario.id_usuario AND
							Foro_Usuario.id_chat_foro=?;''' % (
							filtro_valido, nexo1, filtro_alumnos, nexo2),
																(id_chat,))

		datos = {}	#	Guardar los datos recuperados en este diccionario

		for fila in consulta:

			usuario = {}

			usuario['telegram_user'] = telegram.User(id=fila[0],
													first_name=fila[1],
													is_bot=False,
													last_name=fila[2],
													username=fila[3]
										)

			usuario['id_chat'] = fila[4]
			usuario['fecha_registro'] = fila[5]
			usuario['tipo'] = fila[6]
			usuario['valido'] = fila[7]
			usuario['ban'] = fila[8]
			usuario['n_avisos'] = fila[9]

			#	Se añade el usuario a los datos
			datos[fila[0]] = usuario

			self.__log.debug('Encontrado usuario %s con id=%d en el foro con'\
								' id=%d' % (usuario['telegram_user'].full_name,
								fila[0], id_chat))

		#	Cerrar el cursor y el semáforo
		cursor.close()
		mutex.release()

		if not datos:
			self.__log.debug('No encontrado ningún usuario en el '\
													'foro con id=%d' % id_chat)
			self.__log.debug('Finaliza la ejecución de la función '\
									'"listUsuarios_in_Foro" de "BotServerDAO"')
			return None
		else:
			self.__log.debug('Finaliza la ejecución de la función '\
									'"listUsuarios_in_Foro" de "BotServerDAO"')
			return datos

	def existsUsuarioAnyForo(self, id_usuario: int):

		"""Permite conocer si un usuario se halla registardo en al menos,
			un foro docente

		Argumentos:
		-----------
		id_usuario: int
			Identificador del usuario al cual se desea aplicar la comprobación

		Devuelve:
		---------
			bool. True si el usuario se encuentra en al menos un foro docente
					o False en caso contrario
		"""

		self.__log.debug('Ejecutada función "existsUsuarioAnyForo" de'\
															' "BotServerDAO"')

		#	Se comprueban que los datos sean válidos
		if not isinstance(id_usuario, int):
			raise ValueError('"id_usuario" debe de ser int')

		#	Tomar el cursor y el semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar consulta
		self.__log.debug('Ejecutando consulta con id_usuario = %d' % id_usuario)
		mutex.acquire()

		existe = bool(cursor.execute(
						'SELECT * FROM Foro_Usuario WHERE id_usuario=? LIMIT 1',
													(id_usuario,)).fetchone())


		#	Cerrar el cursor y el semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalziada función "existsUsuarioAnyForo" de'\
															' "BotServerDAO"')

		return existe

	def addUsuarioForo(self, id_chat: int, usuarios, ban=False, n_avisos=0):

		"""
		Permite registrar uno o más usuarios en un foro

		Parámetros:
		-----------
		id_chat: int
			Id de chat asignado al grupo o supergrupo asociado al foro
		usuarios: (int o list[int])
			Ids de los usuarios a registrar en el grupo docente
		ban: bool
			Indica si los usuarios se hallan baneados en el grupo o no.
		n_avisos: int
			Número de avisos dados a un usuario por el envío de
					mensajes no pertenecientes al ámbito académico
		"""

		self.__log.debug('Ejecutada función "addUsuarioForo" de "BotServerDAO"')

		#	Comprobar que los datos sean válidos
		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe de ser int')

		if not isinstance(usuarios, (int,list)):
			raise ValueError('"usuarios" debe de ser int o una lista de int')

		if not isinstance(ban, bool):
			raise ValueError('"ban" debe de ser bool')

		if not isinstance(n_avisos, int):
			raise ValueError('"n_avisos" debe de ser int')

		#	tomar un cursor para insertar datos y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Se intentan insertar los datos en la tabla
		if isinstance(usuarios, int):
			datos = (id_chat, usuarios, ban, n_avisos)
		else:
			datos = [(id_chat, x, ban, n_avisos) for x in usuarios]


		#	Se inserta cada usuario perteneciente en la tabla
		self.__log.debug('Insertando los siguientes datos en la '\
						'tabla Foro_Usuario: ban={}, n_avisos={} para'\
						' id_chat={} e id_usuario={}'.format(ban, n_avisos,
														id_chat, usuarios))
		mutex.acquire()

		cursor.execute('INSERT INTO Foro_Usuario VALUES(?,?,?,?);',datos)


		#	Realizar el commit
		self.__con_bd.commit()

		#	Cerrar el cursor y liberar el semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Fin de ejecución de la función "addUsuarioForo" de '\
															'"BotServerDAO"')

	def editUsuarioForo(self, id_chat: int, usuarios: list or int,
													ban=None, n_avisos=None):

		"""Permite editar los datos del estado de uno o más Usuarios en un Foro.
			Se deben de proporcionar únicamente los parámetros de los valores
			que se desean editar e "id_chat" y al menos el id de un usuario

		Parámetros:
		----------
				id_chat: int
					Id de chat asignado al grupo o supergrupo asociado al foro
				usuarios: (int o list[int])
					Ids de los usuarios a registrar en el grupo docente
				ban: bool
					Indica si los usuarios se hallan baneados en el grupo o no.
				n_avisos: int
					Número de avisos dados a un usuario por el envío de
							mensajes no pertenecientes al ámbito académico
		"""

		self.__log.debug('Ejecutada función "editUsuarioForo" de '\
															'"BotServerDAO"')

		#	Se toma un cursor para editar datos y un semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Se va a construir la consulta en función de los datos proporcionados
		datos = []
		campos = ''

		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe ser int')


		if isinstance(usuarios, int):
			usuarios='(%s)' % str(usuarios) # Se convierte en tupla texto
		elif isinstance(usuarios, list):

			#	Se convierte en tupla texto
			aux = []

			for i in usuarios:

				aux.append(str(i))

				if type(i) != int:
					raise ValueError('"usuarios" contiene un valor que no es int')

			usuarios = '('+','.join(aux)+')'

		else:
			raise ValueError('"usuarios" debe de ser un entero o una lista')

		if ban is not None:

			if not isinstance(ban, bool):
				raise ValueError('"ban" debe ser bool')

			datos.append(ban)
			campos += 'ban=?,'

		if n_avisos is not None:

			if not isinstance(n_avisos, int):
				raise ValueError('"n_avisos" debe ser int')

			datos.append(n_avisos)
			campos += 'n_avisos=?,'


		if datos:
			campos = campos[:-1]	#	Borrar coma sobrante
			datos.append(id_chat)		#	Añadir al usuario
		else:
			# No se ha especificaado ningún campo a modificar y no se hace nada
			raise ValueError('Se debe de proporcionar al menos un parámetro')

		#	Se ejecuta la actualización
		self.__log.debug('Se ejecuta la sentencia de actualización '\
						'con datos ban={} y n_avisos={} para'\
						' id_chat={} e id_usuario={}'.format(ban, n_avisos,
														id_chat, usuarios))
		mutex.acquire()

		cursor.execute('''UPDATE Foro_Usuario
								SET %s WHERE id_chat_foro=?
									AND id_usuario IN %s;''' % (campos,
																usuarios),
																tuple(datos))

		self.__con_bd.commit()	#	Realiza el commit

		#	Cerrar cursor y semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Actualización realizada con éxito, fin de ejecución'\
						' de la función "editUsuarioForo" de "BotServerDAO"')


	def removeUsuarioForo(self, id_chat: int, usuarios: list or int):

		"""Permite eliminar el estado de uno o más usuarios en un foro docente.

		Parámetros:
		-----------
		id_chat: int
			Id de chat asignado al grupo o supergrupo asociado al foro

		usuarios: (int o list[int])
			Ids de los usuarios a registrar en el grupo docente
		"""

		self.__log.debug('Ejecutada función "removeUsuarioForo" de'\
															' "BotServerDAO"')

		#	Se toma un cursor para eliminar datos y un semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Comprobar que los datos proporcionados sean válidos y prrpararlos
		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe ser int')

		if isinstance(usuarios, int):
			usuarios='(%s)' % str(usuarios) # Se convierte en tupla texto
		elif isinstance(usuarios, list):

			#	Se convierte en tupla texto
			aux = []

			for i in usuarios:

				aux.append(str(i))

				if type(i) != int:
					raise ValueError('"usuarios" contiene un valor'\
															' que no es int')

			usuarios = '('+','.join(aux)+')'

		else:
			raise ValueError('"usuarios" debe de ser un entero o una lista')

		#	Se ejecuta el borrado
		self.__log.debug('Se ejecuta la sentencia de borrado con datos'\
						' id_chat=%d y para los usuarios con id en %s' % (
														id_chat, usuarios))
		mutex.acquire()

		cursor.execute('''DELETE FROM Foro_Usuario
							WHERE id_chat_foro=?
							AND id_usuario IN %s;''' % usuarios, (id_chat,))

		self.__con_bd.commit()	#	Realiza el commit

		#	Cerrar el cursor y el semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Borrado realizada con éxito, fin de ejecución de la'\
		' función "removeUsuarioForo" de "BotServerDAO"')


	def addMensaje(self, recibido: bool, id_mensaje_chat: int,
						id_usuario_emisor_receptor=None, id_chat=None,
						fecha=None, academico=False,
						texto=None, multimedia=None,
						editado=False,
						id_mensaje_chat_respondido=None,
						pregunta_formulada=None,
						pregunta_respondida=False) -> int:

		"""Permite añadir un mensaje a la base de datos.

		Parámetros:
		recibido: bool
			Permite determinar si el mensaje fue recibido (True) o
			enviado (False)

		id mensaje chat: int
			Identificador asociado por la plataforma de mensajerı́a al Mensaje en
			el chat en el que se mandó.

		id_usuario_emisor_receptor: Id del usuario emisor del mensaje o receptor
			para el caso de los chats privados, en caso contrario dejar a None

		id_chat: Id del chat del foro docente al que el mensaje fue enviado
				o recibido. Para chats privados dejar en None.

		fecha: datetime.datetime
			Fecha en la que el mensaje fue enviado o recibido

		academico: bool
			Indica si el mensaje pertenece al ámbito académico o no. Sólo aplica
			sentido para mensajes recibidos en chats grupales.
			Por defecto es False

		texto: str
			Contenido del texto que de desea añadir al mensaje.
			Se puede agregar luego haciendo uso de la función addDato y
			addDatoTexto

		multimedia: dict
			Dato multimedia incluído con el mensaje. Se puede agregar después
			mediante las funciones addDato y addDatoArchivo

		editado: bool
			Indica si el mensaje edita a otro mensaje registrado anteriormente.
			Por defecto es False

		id_mensaje_chat_respondido: int
			Identificador de chat del mensaje al cual responde este mensaje

		pregunta_formulada: str
			Representa la pregunta que ha sido formulada dentro del mensaje
			(si la hay). Se debe de usar conjuntamente con pregunta_respondida

		pregunta_respondida: bool
			Indica si la pregunta formulada fue respondida (True) o no, se debe
			de utilizar conjuntamente con pregunta_formulada

		Devuelve:
		---------
			int: Identificador asociado al mensaje

		"""

		self.__log.debug('Iniciada función "addMensaje" de "BotServerDAO"')

		#	Comprobar los datos de entrada
		if not isinstance(id_mensaje_chat, int):
			raise ValueError('"id_mensaje_chat" debe de ser int')

		if (id_usuario_emisor_receptor and
								not isinstance(id_usuario_emisor_receptor, int)):
			raise ValueError('"id_usuario_emisor_receptor" debe de ser int')

		if id_chat and not isinstance(id_chat, int):
				raise ValueError('"id_chat" debe de ser int')

		if fecha and not isinstance(fecha, datetime.datetime):
				raise ValueError('"id_chat" debe de ser de tipo'\
														' "datetime.datetime"')
		else:
			fecha = datetime.datetime.now()

		if academico and not isinstance(academico, bool):
				raise ValueError('"academico" debe ser bool')

		if not isinstance(editado, bool):
				raise ValueError('"editado" debe de ser bool')

		if (id_mensaje_chat_respondido and
							not isinstance(id_mensaje_chat_respondido, int)):
				raise ValueError('"id_mensaje_chat_respondido" debe de ser int')

		if multimedia:
			if ('tipo' not in multimedia or
	not (multimedia['tipo'] in BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO'] or
					multimedia['tipo'] in ('contacto', 'localizacion'))):
				raise ValueError('El "tipo" del dato multimedia debe de ser'\
								' proporcionado o no es válido')

		if pregunta_formulada and not isinstance(pregunta_formulada, str):
			raise ValueError('"pregunta_formulada" debe de ser str')

		if pregunta_respondida and not isinstance(pregunta_respondida, bool):
			raise ValueError('"pregunta_respondida" debe de ser bool')

		#	Preparar el cursor y el semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Se ejecutan todas las inserciones
		self.__log.debug('Ejecutando inserciones')
		mutex.acquire()

		#	Insertar en Evento
		cursor.execute('INSERT INTO Evento(fecha) VALUES(?);', (fecha,))
		id_mensaje = cursor.execute('SELECT last_insert_rowid()').fetchone()[0]

		#	Insertar Mensaje
		cursor.execute('INSERT INTO Mensaje VALUES(?, ?, ?);',
						(id_mensaje, id_mensaje_chat, True))

		#	Insertar en MensajeRecibidoPublico o MensajeRecibidoPrivado
		if recibido:
			if id_chat:
				cursor.execute(
						'INSERT INTO MensajeRecibidoPublico VALUES(?,?,?,?);',
						(id_mensaje, academico, id_usuario_emisor_receptor,
							id_chat))

				if pregunta_formulada:
					cursor.execute('''INSERT INTO PreguntaEfectuadaChatGrupal
										VALUES(?,?,?)''',
										(id_mensaje, pregunta_formulada,
										pregunta_respondida))
			else:
				cursor.execute('INSERT INTO MensajeRecibidoPrivado VALUES(?,?);',
									(id_mensaje,  id_usuario_emisor_receptor))

				if pregunta_formulada:
					cursor.execute('''INSERT INTO PreguntaEfectuadaChatPrivado
										VALUES(?,?,?)''',
										(id_mensaje, pregunta_formulada,
										pregunta_respondida))
		else:
			if id_chat:
				cursor.execute('INSERT INTO MensajeEnviadoPublico VALUES(?,?);',
							(id_mensaje, id_chat))
			else:
				cursor.execute('INSERT INTO MensajeEnviadoPrivado VALUES(?,?);',
									(id_mensaje,  id_usuario_emisor_receptor))

		#	Registrar la edición de un mensaje
		if editado:

			#	Buscar la id asignada al mensaje referenciado en todos los
			#	subtipos de Mensaje
			id_mensaje_editado = cursor.execute(
							'''SELECT id
								FROM
								(SELECT MensajeEnviadoPrivado.id AS id,
									Evento.fecha AS fecha,
									id_usuario_destinatario AS id_chat,
									id_mensaje_chat
								FROM MensajeEnviadoPrivado, Mensaje, Evento
								WHERE Mensaje.id=MensajeEnviadoPrivado.id
								AND Evento.id=Mensaje.id
								AND id_mensaje_chat=?
								AND id_chat=?
								UNION
								SELECT MensajeEnviadoPublico.id AS id,
									Evento.fecha AS fecha,
									id_chat_foro_destino AS id_chat,
									id_mensaje_chat
								FROM MensajeEnviadoPublico, Mensaje, Evento
								WHERE Mensaje.id=MensajeEnviadoPublico.id
								AND Evento.id=Mensaje.id
								AND id_mensaje_chat=?
								AND id_chat=?
								UNION
								SELECT MensajeRecibidoPrivado.id AS id,
									Evento.fecha AS fecha,
									id_usuario_emisor AS id_chat,
									id_mensaje_chat
								FROM MensajeRecibidoPrivado, Mensaje, Evento
								WHERE Mensaje.id=MensajeRecibidoPrivado.id
								AND Evento.id=Mensaje.id
								AND id_mensaje_chat=?
								AND id_chat=?
								UNION
								SELECT MensajeRecibidoPublico.id AS id,
									Evento.fecha AS fecha,
									id_chat_foro AS id_chat,
									id_mensaje_chat
								FROM MensajeRecibidoPublico, Mensaje, Evento
								WHERE Mensaje.id=MensajeRecibidoPublico.id
								AND Evento.id=Mensaje.id
								AND Mensaje.id_mensaje_chat=?
								AND id_chat=?
								ORDER BY fecha
								)
								WHERE id <> %d;''' % id_mensaje,
								(id_mensaje_chat,
									id_usuario_emisor_receptor,
								id_mensaje_chat,
									id_chat,
								id_mensaje_chat,
									id_usuario_emisor_receptor,
								id_mensaje_chat,
									id_chat)).fetchone()[0]

			cursor.execute('UPDATE Mensaje SET existente=? WHERE id=?',
							(False, id_mensaje_editado))

			cursor.execute('INSERT INTO Mensaje_Mensaje_Editado VALUES (?,?);',
							(id_mensaje, id_mensaje_editado))

		#	Registrar la edición de un mensaje
		if id_mensaje_chat_respondido:

			#	Buscar la id asignada al mensaje referenciado en todos los
			#	subtipos de Mensaje
			id_mensaje_respondido = cursor.execute(
								'''SELECT id
									FROM
									(SELECT MensajeEnviadoPrivado.id AS id,
										id_usuario_destinatario AS id_chat,
										id_mensaje_chat
									FROM MensajeEnviadoPrivado, Mensaje
									WHERE Mensaje.id=MensajeEnviadoPrivado.id
									AND Mensaje.id_mensaje_chat=?
									AND id_chat=?
									AND existente=1
									UNION
									SELECT MensajeEnviadoPublico.id AS id,
										id_chat_foro_destino AS id_chat,
										id_mensaje_chat
									FROM MensajeEnviadoPublico, Mensaje
									WHERE Mensaje.id=MensajeEnviadoPublico.id
									AND Mensaje.id_mensaje_chat=?
									AND id_chat=?
									AND existente=1
									UNION
									SELECT MensajeRecibidoPrivado.id AS id,
										id_usuario_emisor AS id_chat,
										id_mensaje_chat
									FROM MensajeRecibidoPrivado, Mensaje
									WHERE Mensaje.id=MensajeRecibidoPrivado.id
									AND Mensaje.id_mensaje_chat=?
									AND id_chat=?
									AND existente=1
									UNION
									SELECT MensajeRecibidoPublico.id AS id,
										id_chat_foro AS id_chat,
										id_mensaje_chat
									FROM MensajeRecibidoPublico, Mensaje
									WHERE Mensaje.id=MensajeRecibidoPublico.id
									AND Mensaje.id_mensaje_chat=?
									AND id_chat=?
									AND existente=1
									);''',
								(id_mensaje_chat_respondido,
									id_usuario_emisor_receptor,
								id_mensaje_chat_respondido,
									id_chat,
								id_mensaje_chat_respondido,
									id_usuario_emisor_receptor,
								id_mensaje_chat_respondido,
									id_chat)).fetchone()

			if id_mensaje_respondido:
				id_mensaje_respondido = id_mensaje_respondido[0]

				cursor.execute(
							'INSERT INTO Mensaje_Mensaje_Editado VALUES (?,?);',
							(id_mensaje, id_mensaje_respondido))

		# Hacer el commit
		self.__con_bd.commit()

		#	Insertar el texto
		if texto:
			self.addDatoTexto(fecha_creacion=fecha, texto=texto,
								id_mensaje=id_mensaje, use_mutex=False)

		#	Insertar los datos multimedia
		if multimedia:
			if multimedia['tipo'] == 'contacto':
				self.addDatoContacto(
	fecha_creacion=fecha,
	telefono=multimedia['telefono'] if 'telefono' in multimedia else None,
	nombre=multimedia['nombre'] if 'nombre' in multimedia else None,
	apellidos=multimedia['apellidos'] if 'apellidos' in multimedia else None,
	id_usuario=multimedia['id_usuario'] if 'id_usuario' in multimedia else None,
	vcard=multimedia['vcard'] if 'vcard' in multimedia else None,
	id_mensaje=id_mensaje, use_mutex=False)

			elif multimedia['tipo'] == 'localizacion':
				self.addDatoLocalizacion(
	fecha_creacion=fecha,
	longitud=multimedia['longitud'] if 'longitud' in multimedia else None,
	latitud=multimedia['latitud'] if 'latitud' in multimedia else None,
	titulo=multimedia['titulo'] if 'titulo' in multimedia else None,
	direccion=multimedia['direccion'] if 'direccion' in multimedia else None,
	id_cuadrante=multimedia['id_cuadrante'] if 'id_cuadrante' in multimedia else None,
	tipo_cuadrante=multimedia['tipo_cuadrante'] if 'tipo_cuadrante' in multimedia else None,
	id_mensaje=id_mensaje, use_mutex=False)

			else:
				self.addDatoArchivo(fecha_creacion=fecha,
	tipo=multimedia['tipo'],
	ruta_archivo=multimedia['ruta_archivo'] if 'ruta_archivo' in multimedia else None,
	file_id=multimedia['file_id'] if 'file_id' in multimedia else None,
	mime_type=multimedia['mime_type'] if 'mime_type' in multimedia else None,
	sticker_emoji=multimedia['sticker_emoji'] if 'sticker_emoji' in multimedia else None,
	sticker_conjunto=multimedia['sticker_conjunto'] if 'sticker_conjunto' in multimedia else None,
	sticker_tipo=multimedia['sticker_tipo'] if 'sticker_tipo' in multimedia else None,
	use_mutex=False)

		#	Cerrar el cursor y el semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "addMensaje" de "BotServerDAO"')
		return id_mensaje

	def addMensajeRespuesta(self, id_mensaje: int,
							pregunta: str,
							respondido: bool):

		"""Permite registrar una pregunta respondida o no en un mensaje que
			la contiene

		Atributos:
		----------

		id_mensaje: int
			Identificador del mensaje al cual se desea añadir la preguta
			(no se debe de confundir con el id de chat del mensaje)

		pregunta_formulada: str
			Representa la pregunta que ha sido formulada dentro del mensaje
			(si la hay). Se debe de usar conjuntamente con pregunta_respondida

		pregunta_respondida: bool
			Indica si la pregunta formulada fue respondida (True) o no, se debe
			de utilizar conjuntamente con pregunta_formulada
		"""

		self.__log.debug('Iniciada función "addMensajeRespuesta" de "BotServerDAO"')

		#	Comprobar los datos de entrada
		if not isinstance(id_mensaje, int):
			raise ValueError('"id_mensaje" debe de ser int')

		if not isinstance(pregunta, str):
			raise ValueError('"pregunta" debe de ser str')

		if not isinstance(respondido, bool):
			raise ValueError('"respondido" debe de ser bool')

		#	Tomar cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar las inserciones
		self.__log.debug('Insertando valores: pregunta=%s y '\
							'respondido=%s para id_mensaje=%d' % (pregunta,
																	respondido,
																	id_mensaje))
		mutex.acquire()

		cursor.execute('''INSERT INTO PreguntaEfectuadaChatGrupal
							SELECT ?, ?, ?
							WHERE EXISTS
							(SELECT id FROM MensajeRecibidoPublico
								WHERE id=?);''',
								(id_mensaje, pregunta, respondido, id_mensaje))

		#	Realizar el commit
		self.__con_bd.commit()

		#	Cerrar cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "addMensajeRespuesta" de "BotServerDAO"')

	def addEventoChatGrupal(self, tipo: str, id_usuario: int, id_chat: int,
							fecha: datetime.datetime) -> int:

		"""Permite registrar un evento de chat grupal

		Atributos:
		----------

		tipo: str
			Tipo de evento acontencido, se permiten los siguientes valores:
			"entrada", "salida", "registro", "ban", "readmision" y "expulsion"

		id_usuario: int
			Identificador del usuario implicado en el suceso del registro

		id_chat: int
			Identificador del foro docente asociado al evento

		fecha: datetime.datetime
			Fecha en la que se produce el evento

		Devuelve:
		---------
			int: Identificador del evento almacenado
		"""

		self.__log.debug('Iniciada función "addEventoChatGrupal" de '\
							'"BotServerDAO"')

		#	Comprobar los datos de entrada
		if not isinstance(tipo, str):
			raise ValueError('"tipo" debe de ser str')
		else:
			tipo = BotServerDAO.__BD_TIPOS['TIPO_EVENTO_CHAT_GRUPAL'][tipo]

		if not isinstance(id_usuario, int):
			raise ValueError('"id_usuario" debe de ser int')

		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe de ser int')

		if not isinstance(fecha, datetime.datetime):
			raise ValueError('"fecha" debe de ser objeto de '\
								'tipo datetime.datetime')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar inserciones
		self.__log.debug('Insertando valores: tipo=%s, '\
							'id_usuario=%d, id_chat=%d y fecha=%s' % (
											tipo, id_usuario, id_chat, fecha))
		mutex.acquire()

		cursor.execute('INSERT INTO Evento(fecha) VALUES (?)', (fecha,))
		id_evento = cursor.execute('SELECT last_insert_rowid();').fetchone()[0]

		cursor.execute('INSERT INTO EventoChatGrupal VALUES (?,?,?,?);',
						(id_evento, tipo, id_usuario, id_chat))

		#	Realizar commit
		self.__con_bd.commit()

		#	Cerrar cursor y semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "addEventoChatGrupal" de "BotServerDAO"')
		return id_evento

	def addComunicado(self,
						fecha_envio: datetime.datetime,
						id_docente_emisor: int,
						ids_chat_foro: list or int) -> int:

		"""Permite registrar un Comunicado pendiente de envío en la base
			de datos

		Atributos:
		----------

		fecha_envio: datetime.datetime
			Fecha en la que se enviará el comunicado

		id_docente_emisor: int
			Identificador de Usuario del usuario docente que solicitó el envío
			del Comunicado

		id_chat_foro: list o int
			Identificadores de los chats de los foros docentes a los cuales
			va dirigido el comunicado

		Devuelve:
		---------
			int: Identificador del Comunicado
		"""

		self.__log.debug('Iniciada función "addComunicado" de "BotServerDAO"')

		#	Comprobar y procesar los parámetros de entrada
		if not isinstance(fecha_envio, datetime.datetime):
			raise ValueError('"fecha_envio" debe de ser objeto de tipo '\
															'datetime.datetime')


		if not isinstance(id_docente_emisor, int):
			raise ValueError('"id_docente_emisor" debe de ser int')


		if isinstance(ids_chat_foro, list):

			for id_chat_foro in ids_chat_foro:
				if type(id_chat_foro) != int:
					raise ValueError('"ids_chat_foro" contiene algún valor '\
																'que no es int')

		elif type(ids_chat_foro) == int:
			ids_chat_foro = [ids_chat_foro]

		else:
			raise ValueError('"ids_chat_foro" debe de ser un int o lista de int')

		#	Obtener el cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar las inserciones
		mutex.acquire()

		datos = (fecha_envio, id_docente_emisor)
		self.__log.debug('Insertando valores fecha_envio={}, '\
						'id_docente_emisor={} y con id_chat_foro en {}'.format(
						fecha_envio, id_docente_emisor, ids_chat_foro))

		cursor.execute('''INSERT INTO
							Comunicado(fecha_envio, id_docente)
							VALUES (?,?);''',
							datos)

		id_comunicado = cursor.execute('SELECT last_insert_rowid();').fetchone()[0]

		for id_chat_foro in ids_chat_foro:
			#	Se registran todos los foros a los que va dirigido el Comunicado
			datos = (id_comunicado, id_chat_foro)
			cursor.execute('INSERT INTO Comunicado_Foro VALUES(?,?);', datos)

		#	Realizar commit
		self.__con_bd.commit()

		#	Cerrar el cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "addComunicado" de "BotServerDAO"')

		return id_comunicado

	def listComunicados(self) -> OrderedDict:

		"""Permite listar todos los Comunicados pendientes de envío

		Devuelve:
		---------
			OrderedDict, None
				Diccionario con el par id_comunicado (int)-datos (dict)

			datos constituye a su vez un diccionario con los siguientes campos:
			- fecha_envio: datetime.datetime
				Fecha de envío del Comunicado

			- docente_emisor: str
				Nombre completo del Uuario docente que lo programó

			- foros: dict
				Dicionario con el par: id_chat (int) - nombre_foro (str)
		"""

		self.__log.debug('Iniciada función "listComunicados" de "BotServerDAO"')

		#	Obtener cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar consulta
		self.__log.debug('Realizando consulta')
		mutex.acquire()

		consulta = cursor.execute(
						'''SELECT Comunicado.id, Comunicado.fecha_envio,
								CASE Usuario.apellidos
									WHEN NULL THEN Usuario.nombre
									ELSE Usuario.nombre||\' \'||Usuario.apellidos
									END,
								Foro.id_chat, Foro.nombre
							FROM Comunicado, Comunicado_Foro, Foro, Usuario
							WHERE Comunicado.id=Comunicado_Foro.id_comunicado
									AND Comunicado_Foro.id_chat_foro=Foro.id_chat
									AND COmunicado.id_docente=Usuario.id
							GROUP BY Comunicado.id;''')

		comunicados = {}

		for fila in consulta:

			#	Añadir los datos de cada comunicado diferente en el diccionario
			if fila[0] not in comunicados:
				comunicados[fila[0]] = {
										'fecha_envio': fila[1],
										'docente_emisor': fila[2],
										'foros': {}
									}
									#	'anclar': fila[2],
			#	Añadir cada foro docente en el que se halle registrado
			comunicados[fila[0]]['foros'][fila[3]] = fila[4]

		#	Cerrar cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "listComunicados" de "BotServerDAO"')


		return comunicados if comunicados else None

	def getComunicado(self, id_comunicado: int):

		"""Permite obtener los datos y el contenido de un Comunicado

		Recibe:
		-------
		id_comunicado: int
			Identificador del Comunicado cuya infromación se desea obtener

		Devuelve:
			dict: Compuesto por lo siguiente:
			- fecha_envio: datetime.datetime
				Fecha de envío del Comunicado

			- docente_emisor: str
				Nombre completo del Uuario docente que lo programó

			- datos: OrderedDict
				Diccionario ordenado que consta del par:
				id_dato (int) - dato (dict)

			En concreto, datos puede presentar los siguientes formatos

			Para tipo texto:

			·tipo_dato: 'texto'
			·contenido: str o list str
			 	Texto o textos a almacenar

			Para tipo Multimedia con Archivo:

			·tipo_dato: str
				Tipo de Dato Multimedia almacenado: Puede adoptar los valores
				'imagen', 'audio', 'video'. 'nota_voz', 'nota_video',
				'documento','animacion' y 'sticker'

			contenido: str o None
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

			·telefono: str
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
				Identificador del cuadrante asociado a la avenida localizada en la
				Localizacion. Parámetro opcional

			·tipo cuadrante: str o None
				Tipo de cuadrante asociado a la avenida localizada en la
				Localizacion.
				Parámetro opcional

			- foros: dict
				Dicionario con el par: id_chat (int) - nombre_foro (str)
		"""

		self.__log.debug('Iniciada función "getComunicado" de "BotServerDAO"')

		#	Comprobar y procesar los parámetros de entrada
		if not isinstance(id_comunicado, int):
			raise ValueError('"id_comunicado" no es int')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar consulta
		self.__log.debug('Realizando consulta con id_comunicado=%d' % id_comunicado)
		mutex.acquire()

		cursor.execute('''SELECT fecha_envio, id_docente
							FROM Comunicado
							WHERE id=?''', (id_comunicado,))
		datos = cursor.fetchone()

		#if not datos:
		#	return None

		comunicado = {
						'fecha_envio': datos[0],
						'docente_emisor': datos[1]
					}

		#	Tomar los textos
		comunicado['datos'] = OrderedDict()

		consulta = cursor.execute(
						'''SELECT
							DatoTextoMultimedia.id AS id_dato,
							DatoTextoMultimedia.fecha_creacion AS fecha_creacion,
							DatoTextoMultimedia.tipo AS
												"tipo_dato [TIPO_DATOARCHIVO]",
							DatoTextoMultimedia.contenido AS contenido,
							DatoTextoMultimedia.file_id AS file_id,
							DatoTextoMultimedia.mime_type AS mime_type,
							DatoTextoMultimedia.sticker_emoji AS sticker_emoji,
							DatoTextoMultimedia.conjunto AS sticker_conjunto,
							DatoTextoMultimedia.tipo_sticker AS
												"tipo_sticker [TIPO_STICKER]",
							DatoTextoMultimedia.telefono AS telefono,
							DatoTextoMultimedia.nombre AS nombre,
							DatoTextoMultimedia.apellidos AS apellidos,
							DatoTextoMultimedia.id_usuario AS id_usuario,
							DatoTextoMultimedia.vcard AS vcard,
							DatoTextoMultimedia.longitud AS longitud,
							DatoTextoMultimedia.latitud AS latitud,
							DatoTextoMultimedia.direccion AS direccion,
							DatoTextoMultimedia.id_cuadrante AS id_cuadrante,
							DatoTextoMultimedia.tipo_cuadrante AS tipo_cuadrante
							FROM
								(SELECT DatoArchivo.id, fecha_creacion, tipo,
									ruta_archivo AS contenido, file_id,
									mime_type, NULL AS sticker_emoji,
									NULL AS conjunto, NULL AS tipo_sticker,
									NULL AS telefono, NULL AS nombre,
									NULL AS apellidos,
									NULL AS id_usuario, NULL AS vcard,
									NULL AS longitud, NULL AS latitud,
									NULL AS titulo, NULL AS direccion,
									NULL AS id_cuadrante, NULL AS tipo_cuadrante
									FROM DatoArchivo, Dato WHERE tipo <> %d
									AND Dato.id=DatoArchivo.id
								UNION
								SELECT DatoArchivo.id, fecha_creacion,
									DatoArchivo.tipo AS tipo,
									ruta_archivo AS contenido,
									file_id, mime_type, emoji AS sticker_emoji,
									conjunto,
									DatoArchivoSticker.tipo AS tipo_sticker,
									NULL AS telefono, NULL AS nombre,
									NULL AS apellidos,
									NULL AS id_usuario, NULL AS vcard,
									NULL AS longitud, NULL AS latitud,
									NULL AS titulo, NULL AS direccion,
									NULL AS id_cuadrante, NULL AS tipo_cuadrante
									FROM DatoArchivo, DatoArchivoSticker,
										Dato
									WHERE
									DatoArchivo.id = DatoArchivoSticker.id
									AND DatoArchivo.id=Dato.id
								UNION
								SELECT DatoTexto.id, fecha_creacion,
									\'texto\' as tipo,
									texto AS contenido,
									NULL AS file_id, NULL AS mime_type,
									NULL AS sticker_emoji, NULL AS conjunto,
									NULL AS tipo_sticker,
									NULL AS telefono, NULL AS nombre,
									NULL AS apellidos,
									NULL AS id_usuario, NULL AS vcard,
									NULL AS longitud, NULL AS latitud,
									NULL AS titulo, NULL AS direccion,
									NULL AS id_cuadrante, NULL AS tipo_cuadrante
								FROM DatoTexto, Dato
								WHERE DatoTexto.id=Dato.id
								UNION
								SELECT DatoContacto.id, fecha_creacion,
									\'contacto\' as tipo,
									NULL AS contenido,
									NULL AS file_id, NULL AS mime_type,
									NULL AS sticker_emoji, NULL AS conjunto,
									NULL AS tipo_sticker,
									telefono, nombre, apellidos,
									id_usuario, vcard,
									NULL AS longitud, NULL AS latitud,
									NULL AS titulo, NULL AS direccion,
									NULL AS id_cuadrante, NULL AS tipo_cuadrante
								FROM DatoContacto, Dato
								WHERE Dato.id=DatoContacto.id
								UNION
								SELECT DatoLocalizacion.id, fecha_creacion,
									\'localizacion\' as tipo,
									NULL AS contenido,
									NULL AS file_id, NULL AS mime_type,
									NULL AS sticker_emoji, NULL AS conjunto,
									NULL AS tipo_sticker,
									NULL AS telefono, NULL AS nombre,
									NULL AS apellidos,
									NULL AS id_usuario, NULL AS vcard,
									longitud, latitud,
									titulo, direccion,
									id_cuadrante, tipo_cuadrante
								FROM DatoLocalizacion, Dato
								WHERE DatoLocalizacion.id=Dato.id)
									DatoTextoMultimedia, Dato_Comunicado
								WHERE Dato_Comunicado.id_comunicado=? AND
								DatoTextoMultimedia.id=Dato_Comunicado.id_dato
								ORDER BY fecha_creacion;''' % (
					BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO']['sticker'],),
								(id_comunicado,))


		#	Introducir cada dato extraído en en la lista de mensajes organizados
		for m in consulta:

			#	Mapear manualmente el TIPO_DATOARCHIVO a la cadena
			#	correspondiente porque no se ejecuta manuialmente
			tipo_dato = m[2]

			#	Registrar los datos contenidos en el mismo
			if tipo_dato == 'texto':
				#	El dato es texto
				comunicado['datos'][m[0]] = dict(zip(m.keys()[1:4], m[1:4]))
			elif tipo_dato in BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO'] and tipo_dato != 'sticker':
				#	El dato es multimedia diferente de sticker
				comunicado['datos'][m[0]] = dict(zip(m.keys()[1:6], m[1:6]))
			elif tipo_dato == 'sticker':
				#	El dato es multimedia sticker
				comunicado['datos'][m[0]] = dict(zip(m.keys()[1:9], m[1:9]))
			elif tipo_dato == 'contacto':
				#	El dato es contacto
				comunicado['datos'][m[0]] = dict(zip(m.keys()[1:3], m[1:3]))
				comunicado['datos'][m[0]].update(dict(zip(m.keys()[9:14], m[9:14])))
			else:
				#	El dato es una localización
				comunicado['datos'][m[0]] = dict(zip(m.keys()[1:3], m[1:3]))
				comunicado['datos'][m[0]].update(dict(zip(m.keys()[14:], m[14:])))

			#	Cambiar el tipo_datos por su cadena correspondiente
			comunicado['datos'][m[0]]['tipo_dato'] = tipo_dato


		#	Tomar los foros
		comunicado['foros'] = {}

		consulta = cursor.execute(
							'''SELECT Foro.id_chat, Foro.nombre
								FROM Foro, Comunicado_Foro
								WHERE Foro.id_chat=Comunicado_Foro.id_chat_foro
								AND Comunicado_Foro.id_comunicado=?;''',
								(id_comunicado,))

		if consulta:
			for fila in consulta:
				comunicado['foros'][fila[0]] = fila[1]

		#	Cerrar cursor y semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "getComunicado" de "BotServerDAO"')
		return comunicado

	def removeComunicado(self, id_comunicado: int):

		"""Permite eliminar un Comunicado registrado

		Recibe:
		-------
		id_comunicado: int
			Identificador del Comunicado cuya infromación se desea obtener

		Devuelve:
			list de str
			Lista de ficheros asociados a los datos multimedia del comunicado y
			que ya puede ser eliminado
		"""

		self.__log.debug('Iniciada función "removeComunicado" de '\
															'"BotServerDAO"')

		#	Comprobar parámetros de entrada
		if not isinstance(id_comunicado, int):
			raise ValueError('"id_comunicado" debe de ser un int')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar borrados
		self.__log.debug('Borrando Comunicado con id=%s' % str(id_comunicado))
		mutex.acquire()

		#	Borrar todos los datos asociados al comunicado
		consulta = cursor.execute('''SELECT id_dato
								FROM Dato_Comunicado
								WHERE id_comunicado=?;''',
								(id_comunicado,))

		id_dato = BotServerDAO.__to_sql_tuple(consulta.fetchall())

		#	Lista de archivos a borrar
		arch_borr = None

		if id_dato:

			#	Conocer todos los archivos borrados
			consulta = cursor.execute(
						'''SELECT ruta_archivo
							FROM DatoArchivo, Dato_Comunicado
							WHERE Dato_Comunicado.id_comunicado=?
							AND Dato_Comunicado.id_dato=DatoArchivo.id''',
							(id_comunicado,))
			arch_borr = BotServerDAO.__to_sql_tuple(consulta.fetchall())

			cursor.execute('DELETE FROM DatoTexto WHERE id IN %s' % id_dato)
			cursor.execute(('DELETE FROM DatoArchivoSticker WHERE id IN %s' %
																	id_dato))
			cursor.execute('DELETE FROM DatoArchivo WHERE id IN %s' % id_dato)
			cursor.execute('DELETE FROM DatoContacto WHERE id IN %s' % id_dato)
			cursor.execute(('DELETE FROM DatoLocalizacion WHERE id IN %s' %
																	id_dato))
			cursor.execute(('DELETE FROM Dato_Comunicado WHERE id_dato IN %s' %
																	id_dato))
			cursor.execute('DELETE FROM Dato WHERE id IN %s' % id_dato)

		#	Borrar la lista de foros asignados al comunicado
		cursor.execute('DELETE FROM Comunicado_Foro WHERE id_comunicado=?',
						(id_comunicado,))

		cursor.execute('DELETE FROM Comunicado WHERE id=?', (id_comunicado,))

		#	Realizar commit
		self.__con_bd.commit()

		#	Cerrar cursor y liberar semáforos
		mutex.release()
		cursor.close()

		self.__log.debug('Finalizada función "removeComunicado" de "BotServerDAO"')
		return arch_borr

	def countMensajesForo(self, id_chat: int,
							fecha_inicio: datetime.datetime,
							fecha_fin: datetime.datetime):

		"""Permite contar los mensajes registrados en un Foro Docente

		Recibe:
		-------
		id_chat: int
			Identificador del chat sobre el que se aplica la operación

		fecha_inicio: datetime.datetime
			Fecha de inicio a partir de la cual se empiezan a contar mensajes

		fecha_fin: datetime.datetime
			Fecha de fin a partir de la cual se dejan de contar mensajes
		"""

		self.__log.debug('Iniciada función "countMessagesForo" de'\
															' "BotServerDAO"')

		#	Comprobar los datos de entrada
		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe ser int')

		if not isinstance(fecha_inicio, datetime.datetime):
			raise ValueError('"fecha_inicio" debe ser de tipo datetime.datetime')

		if not isinstance(fecha_fin, datetime.datetime):
			raise ValueError('"fecha_fin" debe ser de tipo datetime.datetime')

		#	Tomar el cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar la sentencia
		self.__log.debug('Realizando consulta con valores id_chat={}, '\
							'desde fecha_inicio={} hasta fecha_fin={}'.format(
								id_chat, fecha_inicio, fecha_fin))
		mutex.acquire()
		cursor.execute('''SELECT a.num+b.num
							FROM
							(SELECT COUNT(MensajeRecibidoPublico.id) AS num
								FROM MensajeRecibidoPublico, Evento
								WHERE id_chat_foro=? AND
									fecha BETWEEN ? AND ?
									AND Evento.id=MensajeRecibidoPublico.id) a,
							(SELECT COUNT(MensajeEnviadoPublico.id) AS num
								FROM MensajeEnviadoPublico, Evento
								WHERE id_chat_foro_destino=? AND
								fecha BETWEEN ? AND ?
								AND Evento.id=MensajeEnviadoPublico.id) b;''',
							(id_chat, fecha_inicio, fecha_fin)*2)

		n_mensajes = cursor.fetchone()[0]

		#	Cerrar cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "countMessagesForo" de "BotServerDAO"')
		return n_mensajes

	def getMensajesForo(self, id_chat: int,
					fecha_inicio: datetime.datetime, fecha_fin: datetime,
					division=None, particion=None):

		"""Permite obtener todos los datos de los mensajes enviados en un foro
			en un intervalo de tiempo específico

		Recibe:
		------
		id_chat: int
			Identificador del chat sobre el que se aplica la operación

		fecha_inicio: datetime.datetime
			Fecha de inicio a partir de la cual se empiezan a recopilar mensajes

		fecha_fin: datetime.datetime
			Fecha de fin a partir de la cual se dejan de recopilar mensajes

		division: int
			Indica el número de particiones en las que se va a dividir la
			recopilación. Este parámetro debe de ser usado conjuntamente con
			paticion

		particion: int
			Indica el número de partición considerada en esta consulta. Este
			parámetro debe de ser usado conjuntamente con "division"


		Devuelve:
			OrderedDict: Diccionario ordenado que consta del par:
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
			·contenido: str o list str
			 	Texto o textos a almacenar

			Para tipo Multimedia con Archivo:

			·tipo_dato: str
				Tipo de Dato Multimedia almacenado: Puede adoptar los valores
				'imagen', 'audio', 'video'. 'nota_voz', 'nota_video',
				'documento','animacion' y 'sticker'

			·contenido: str o None
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

			·telefono: str
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

		self.__log.debug('Iniciada función "getMessagesForo" de "BotServerDAO"')

		#	Comprobar los datos de entrada
		if not isinstance(id_chat, int):
			raise ValueError('"id_chat" debe ser int')

		if not isinstance(fecha_inicio, datetime.datetime):
			raise ValueError('"fecha_inicio" debe ser de tipo datetime.datetime')

		if not isinstance(fecha_fin, datetime.datetime):
			raise ValueError('"fecha_fin" debe ser de tipo datetime.datetime')

		if bool(not division) ^ bool(particion is None):
			raise ValueError('"division" y "particion" deben de presentar '\
								'ambos valores enteros o None')
		else:
			if not isinstance(division, int):
				raise ValueError('"division" debe de ser int')

			if not isinstance(particion, int):
				raise ValueError('"particion" debe de ser int')

		#	Establecer el límite de la particion
		limite = (('LIMIT '+str(division*particion)+', '+
											str(division)) if division else '')

		#	Tomar el cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar consulta
		self.__log.debug('Realizando consulta en foro con id=%d, '\
						'desde %s a %s' % (id_chat, fecha_inicio, fecha_fin))
		mutex.acquire()

		mensaje = OrderedDict()
		consulta = cursor.execute(
'''SELECT MensajePublico.id AS id_mensaje,
MensajePublico.nombre_usuario AS nombre_usuario,
MensajePublico.tipo_usuario
			AS "tipo_usuario [TIPO_USUARIO]",
MensajePublico.fecha AS fecha,
MensajePublico.academico AS academico,
NULL AS evento_mensaje,
DatoTextoMultimedia.id AS id_dato,
DatoTextoMultimedia.tipo AS
			"tipo_dato [TIPO_DATOARCHIVO]",
DatoTextoMultimedia.contenido AS contenido,
DatoTextoMultimedia.file_id AS file_id,
DatoTextoMultimedia.mime_type AS mime_type,
DatoTextoMultimedia.sticker_emoji AS sticker_emoji,
DatoTextoMultimedia.conjunto AS sticker_conjunto,
DatoTextoMultimedia.tipo_sticker
			AS "tipo_sticker [TIPO_STICKER]",
DatoTextoMultimedia.telefono AS telefono,
DatoTextoMultimedia.nombre AS nombre,
DatoTextoMultimedia.apellidos AS apellidos,
DatoTextoMultimedia.id_usuario AS id_usuario,
DatoTextoMultimedia.vcard AS vcard,
DatoTextoMultimedia.longitud AS longitud,
DatoTextoMultimedia.latitud AS latitud,
DatoTextoMultimedia.titulo AS titulo,
DatoTextoMultimedia.direccion AS direccion,
DatoTextoMultimedia.id_cuadrante AS id_cuadrante,
DatoTextoMultimedia.tipo_cuadrante AS tipo_cuadrante
FROM
(SELECT MensajeRecibidoPublico.id, fecha,
	academico,
	CASE WHEN Usuario.apellidos IS NULL
		THEN Usuario.nombre
	ELSE Usuario.nombre||" "||Usuario.apellidos
	END AS nombre_usuario,
	Usuario.tipo AS tipo_usuario, id_chat_foro,
	NULL AS evento_mensaje
FROM MensajeRecibidoPublico, Evento, Mensaje, Usuario
WHERE Mensaje.id=MensajeRecibidoPublico.id AND
	Evento.id=Mensaje.id AND MensajeRecibidoPublico.id_usuario_emisor=Usuario.id
	AND existente=1
UNION
SELECT MensajeEnviadoPublico.id,
	fecha, 1 AS academico,
	"Bot" AS nombre_usuario,
	NULL AS tipo_usuario,
	id_chat_foro_destino AS id_chat_foro,
	NULL AS evento_mensaje
FROM MensajeEnviadoPublico, Evento, Mensaje
WHERE Mensaje.id=MensajeEnviadoPublico.id
	AND Mensaje.id=Evento.id
AND existente=1
%s) MensajePublico,
Dato_Mensaje,
(SELECT id, tipo, ruta_archivo AS contenido,
	file_id, mime_type, NULL AS sticker_emoji,
	NULL AS conjunto, NULL AS tipo_sticker,
	NULL AS telefono, NULL AS nombre,
	NULL AS apellidos,
	NULL AS id_usuario, NULL AS vcard,
	NULL AS longitud, NULL AS latitud,
	NULL AS titulo, NULL AS direccion,
	NULL AS id_cuadrante, NULL AS tipo_cuadrante
	FROM DatoArchivo WHERE tipo <> %d
UNION
SELECT DatoArchivo.id, DatoArchivo.tipo,
	ruta_archivo AS contenido,
	file_id, mime_type, emoji AS sticker_emoji,
	conjunto,
	DatoArchivoSticker.tipo AS tipo_sticker,
	NULL AS telefono, NULL AS nombre,
	NULL AS apellidos,
	NULL AS id_usuario, NULL AS vcard,
	NULL AS longitud, NULL AS latitud,
	NULL AS titulo, NULL AS direccion,
	NULL AS id_cuadrante, NULL AS tipo_cuadrante
	FROM DatoArchivo, DatoArchivoSticker
	WHERE
	DatoArchivo.id = DatoArchivoSticker.id
UNION
SELECT id, \'texto\' as tipo,
	texto AS contenido,
	NULL AS file_id, NULL AS mime_type,
	NULL AS sticker_emoji, NULL AS conjunto,
	NULL AS tipo_sticker,
	NULL AS telefono, NULL AS nombre,
	NULL AS apellidos,
	NULL AS id_usuario, NULL AS vcard,
	NULL AS longitud, NULL AS latitud,
	NULL AS titulo, NULL AS direccion,
	NULL AS id_cuadrante, NULL AS tipo_cuadrante
FROM DatoTexto
UNION
SELECT id, \'contacto\' as tipo,
	NULL AS contenido,
	NULL AS file_id, NULL AS mime_type,
	NULL AS sticker_emoji, NULL AS conjunto,
	NULL AS tipo_sticker,
	telefono, nombre, apellidos,
	id_usuario, vcard,
	NULL AS longitud, NULL AS latitud,
	NULL AS titulo, NULL AS direccion,
	NULL AS id_cuadrante, NULL AS tipo_cuadrante
FROM DatoContacto
UNION
SELECT id, \'localizacion\' as tipo,
	NULL AS contenido,
	NULL AS file_id, NULL AS mime_type,
	NULL AS sticker_emoji, NULL AS conjunto,
	NULL AS tipo_sticker,
	NULL AS telefono, NULL AS nombre,
	NULL AS apellidos,
	NULL AS id_usuario, NULL AS vcard,
	longitud, latitud,
	titulo, direccion,
	id_cuadrante, tipo_cuadrante
FROM DatoLocalizacion)
	DatoTextoMultimedia
WHERE MensajePublico.id=Dato_Mensaje.id_mensaje
AND Dato_Mensaje.id_dato=DatoTextoMultimedia.id
AND MensajePublico.id_chat_foro=?
AND MensajePublico.fecha BETWEEN ? AND ?
UNION
SELECT EventoChatGrupal.id,
CASE WHEN Usuario.apellidos IS NULL
	THEN Usuario.nombre
	ELSE Usuario.nombre||" "||Usuario.apellidos
END AS nombre_usuario,
NULL AS tipo_usuario,
fecha,
1 AS academico,
CASE EventoChatGrupal.tipo
WHEN 0
	THEN Usuario.nombre||" entró en el grupo"
WHEN 1
	THEN Usuario.nombre||" salió del grupo"
WHEN 2
	THEN Usuario.nombre||" fue registrad@"
WHEN 3
	THEN Usuario.nombre||" salió del grupo"
WHEN 4
	THEN Usuario.nombre||" fue banead@ del grupo"
WHEN 5
	THEN Usuario.nombre||" fue expulsad@ del grupo"
ELSE NULL
END AS evento_mensaje,
NULL AS id_dato,
NULL AS
	"tipo_dato [TIPO_DATOARCHIVO]",
NULL AS contenido,
NULL AS file_id,
NULL AS mime_type,
NULL AS sticker_emoji,
NULL AS conjunto,
NULL
	AS "tipo_sticker [TIPO_STICKER]",
NULL AS telefono,
NULL AS nombre,
NULL AS apellidos,
NULL AS id_usuario,
NULL AS vcard,
NULL AS longitud,
NULL AS latitud,
NULL AS titulo,
NULL AS direccion,
NULL AS id_cuadrante,
NULL AS tipo_cuadrante
FROM Evento, EventoChatGrupal, Usuario
WHERE Evento.id=EventoChatGrupal.id
	AND EventoChatGrupal.id_usuario=Usuario.id
AND id_chat_foro=?
AND fecha BETWEEN ? AND ?
ORDER BY fecha;''' % (limite,
BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO']['sticker']),
(id_chat, fecha_inicio, fecha_fin)*2)

		#if not consulta:
		#	return None

		#	Introducir cada dato extraído en en la lista de mensajes organizados
		for m in consulta:

			if not mensaje or m[0] not in mensaje:

				#	Registrar el mensaje
				mensaje[m[0]] = dict(zip(m.keys()[1:5], m[1:5]))

				#	Mapear el tipo de usuario manualmente ya que la consulta
				#	no lo mapea de forma automática
				(mensaje[m[0]]
				['tipo_usuario']) = BotServerDAO.__tipo_usuario_converter(
									mensaje[m[0]]['tipo_usuario'])

				if m[5]:
					#	El mensaje contiene un evento y se añade
					mensaje[m[0]]['evento'] = m[5]
					mensaje[m[0]].pop('tipo_usuario')
					mensaje[m[0]].pop('academico')

					continue
				else:
					#	El mensaje contiene otro tipo de datos
					mensaje[m[0]]['datos'] = OrderedDict()

			#	Registrar los datos contenidos almacenando SOLO los campos
			#	que correspondan
			if m[7] == 'texto':
				#	El dato es texto o un evento
				mensaje[m[0]]['datos'][m[6]] = dict(zip(m.keys()[7:9], m[7:9]))
			elif (m[7] in BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO'] and
															m[7] != 'sticker'):
				#	El dato es multimedia diferente de sticker
				mensaje[m[0]]['datos'][m[6]] = dict(zip(m.keys()[7:11],
																	m[7:11]))
			elif m[7] == 'sticker':
				#	El dato es multimedia sticker
				mensaje[m[0]]['datos'][m[6]] = dict(zip(m.keys()[7:14],
																	m[7:14]))
			elif m[7] == 'contacto':
				#	El dato es contacto
				mensaje[m[0]]['datos'][m[6]] = {m.keys()[7]: m[7]}
				mensaje[m[0]]['datos'][m[6]].update(dict(zip(m.keys()[14:19],
																	m[14:19])))
			else:
				#	El dato es una localización
				mensaje[m[0]]['datos'][m[6]] = {m.keys()[7]: m[7]}
				mensaje[m[0]]['datos'][m[6]].update(dict(zip(m.keys()[19:],
																	m[19:])))

		#	Cerrar cursor y semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "getMessagesForo" de "BotServerDAO"')
		return mensaje

	def addConcepto(self, concepto: str, resumen_concepto: str,
								tipo: str or None, id_concepto=None) -> int:

		"""Permite añadir una nueva pregunta de un Concepto Teórico a
			la base de información.

		Parámetros:
		-----------
		concepto: str
			Pregunta asociada al Concepto Teórico

		resumen_pregunta: str
			Resumen de la pregunta obtenido tras el preprocesamiento de
			la pregunta

		tipo: str o None
			Categoría semántica a la que pertenece la pregunta. None si no
			hay una categoría asociada

		id_concepto: int
			Identificador del concepto teórico existente al que se desea
			asociar la pregunta, dejar en None si se desea asociar a un nuevo
			Concepto

		Devuelve:
			int: Identificador del concepto al cual se ha añadido la pregunta
		"""

		self.__log.debug('Iniciada función "addConcepto" de "BotServerDAO"')

		#	Comprobar los datos de entrada
		if not isinstance(concepto, str):
			raise ValueError('"concepto" debe ser str')

		if not isinstance(resumen_concepto, str):
			raise ValueError('"resumen_concepto" debe ser str')

		if not (isinstance(tipo, str) or tipo is None):
			raise ValueError('"tipo" debe de ser str o None')

		if id_concepto and not isinstance(id_concepto, int):
			raise valueError('"id_concepto" debe de ser int')

		# Modificar la base de datos para meter todos estos campos TODO

		#	Tomar el cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar consulta
		self.__log.debug('Realizando inserciones con valores concepto={}, '\
						'resumen_concepto={} y tipo={}'.format(concepto,
														resumen_concepto, tipo))
		mutex.acquire()

		if not id_concepto:
			cursor.execute('INSERT INTO Concepto DEFAULT VALUES;')
			id_concepto = cursor.execute(
									'SELECT last_insert_rowid();').fetchone()[0]

		#	Insertar pregunta si no había una igual
		cursor.execute('''INSERT INTO ConceptoPregunta
										SELECT ?, ?, ?, ? WHERE NOT EXISTS
											(SELECT id
											FROM ConceptoPregunta
											WHERE resumen_pregunta=?
												AND tipo IS ?);''',
						(concepto, resumen_concepto, tipo, id_concepto,
												resumen_concepto, tipo))

		#	Advertir si ya existía una pregunta con un resumen_concepto y
		#	tipo coincidentes
		if not cursor.execute('SELECT last_insert_rowid();').fetchone():
			self.__log.warning('Ya existe una pregunta similar a "%s" y no se'\
									' va a volver a insertar' % concepto)

		#	Realizar el commit
		self.__con_bd.commit()

		#	Cerrar cursor y liberar semáforo
		mutex.release()
		cursor.close()

		self.__log.debug('Finalizada función "addConcepto" de "BotServerDAO"')
		return id_concepto

	def removeConcepto(self, pregunta: str=None, id_concepto: int=None):

		"""Permite eliminar un Conepto Teórico de la base de información
			conociendo la pregunta asociada al Concepto Teórico o el
			identificador del mismo. Sölo se debe de pasar uno de los dos

		Parámetros:
		-----------
		pregunta: str
			Pregunta asociada al Concepto Teórico

		id_concepto: int
			Identificador del concepto teórico existente al que se desea
			asociar la pregunta, dejar en None si se desea asociar a un nuevo
			Concepto
		"""

		self.__log.debug('Iniciada función "removeConcepto" de "BotServerDAO"')

		#	Comprobar los datos de entrada
		if pregunta and not isinstance(pregunta, str):
			raise ValueError('"pregunta" debe de ser str')

		if id_concepto is not None and not isinstance(id_concepto, int):
			raise ValueError('"id_concepto" debe de ser int')

		if not (bool(pregunta) ^ bool(id_concepto is None)):
			raise ValueError('Se debe de proporcionar "pregunta" o '\
															'"id_concepto"')

		#	Tomar cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar operaciones
		self.__log('Borando información con pregunta={} o '\
								'id_concepto={}'.format(pregunta, id_concepto))
		mutex.acquire()

		if not id_concepto:
			cursor.execute('SELECT id FROM ConceptoPregunta WHERE pregunta=?',
							(pregunta,))
			id_concepto = cursor.fetchone()[0]

		datos_borrados = cursor.execute('''SELECT id_dato
											FROM Dato_Concepto
											WHERE id_concepto=?);''').fetchall()

		datos_borrados = BotServerDAO.__to_sql_tuple(datos_borrados)

		cursor.execute('''DELETE FROM
							DatoTexto
							WHERE id IN %s;''' % datos_borrados)

		cursor.execute('''DELETE FROM
							Dato
							WHERE id IN %s;''' % datos_borrados)

		cursor.execute('DELETE FROM ConceptoPregunta WHERE id=?;',
						(id_concepto,))
		cursor.execute('DELETE FROM Concepto WHERE id=?;',
						(id_concepto,))


		#	Realizar el commit
		self.__con_bd.commit()

		#	Liberar semáforo y cerrar cursor
		mutex.release()
		cursor.close()

		self.__log.debug('Finalizada función "removeConcepto" de "BotServerDAO"')

	def removeAllConceptos(self):

		"""Permite eliminar todos los conetos y sus textos almacenados en
			la base de información

		Nota: Esta función también contempla el hecho de que un Concepto
		lleve asociado DatosMultimedia. No obstante, en la actual versión
		del ejecutable no se contempla este requisito, pero de deja para
		futuras ampliaciones
		"""

		self.__log.debug('Iniciada función "removeAllConceptos" de '\
															'"BotServerDAO"')

		#	Preparar el semáforo
		mutex = Lock()

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar operaciones
		self.__log.debug('Realizando borrado')
		mutex.acquire()

		#	Obtener lista de archivos que deben ser borrados
		consulta = cursor.execute('''SELECT ruta_archivo
										FROM DatoArchivo
										WHERE id IN
										(SELECT id_dato FROM Dato_Concepto);''')

		arch_borr = [fila[0] for fila in consulta]

		consulta = cursor.execute('SELECT id_dato FROM Dato_Concepto;')
		id_dato = [fila[0] for fila in consulta]

		if id_dato:
			id_dato = BotServerDAO.__to_sql_tuple(id_dato)

			cursor.execute('DELETE FROM DatoArchivoSticker WHERE id IN %s;' % id_dato)
			cursor.execute('DELETE FROM DatoArchivo WHERE id IN %s;' % id_dato)
			cursor.execute('DELETE FROM DatoTexto WHERE id IN %s;' % id_dato)
			cursor.execute('DELETE FROM Dato_Concepto WHERE id_dato IN %s;' % id_dato)
			cursor.execute('DELETE FROM Dato WHERE id IN %s;' % id_dato)

		cursor.execute('DELETE FROM ConceptoPregunta;')
		cursor.execute('DELETE FROM Concepto;')

		#	Realizar el commit
		self.__con_bd.commit()

		#	Cerrar cursor y liberar semáforo
		mutex.release()
		cursor.close()

		self.__log.debug('Finalizada función "removeAllConceptos" de '\
															'"BotServerDAO"')
		return arch_borr if arch_borr else None

	def existsConcepto(self, res_preg: str, tipo: str):

		"""Permite conocer si un Concepto definido por su resumen de pregunta
			y su categoría semántica principal existen en la base de información
			o no.

		Parámetros:
		-----------
		res_preg: str
			Resumen de pregunta por el cual se va a realizar la búsqueda

		tipo: str
			Categoría semántica principal a la que pertenece el la pregunta cuyo
			resumen de pregunta se ha proporcionado en "res_preg".

		Devuelve:
		--------
		bool. True si existe un Concepto teórico con un resumen de pregunta y un
			tipo coincidentes o False en caso contrario.

		"""

		self.__log.debug('Iniciada función "existsConcepto" de "BotServerDAO"')

		#	Comprobar los datos de entrada
		if not isinstance(res_preg, str):
			raise ValueError('"res_preg" debe de ser str')

		#	Comprobar los datos de entrada
		if tipo and not isinstance(tipo, str):
			raise ValueError('"tipo" debe de ser str o None')


		#	Tomar cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar consulta
		self.__log.debug('Realizando búsqueda con resumen_pregunta=%s y '\
												'tipo=%s' % (
													res_preg, tipo))
		mutex.acquire()

		consulta = cursor.execute('''SELECT id FROM ConceptoPregunta
										WHERE resumen_pregunta=? AND
										tipo IS ?;''', (res_preg, tipo))

		resultado = bool(consulta.fetchone())

		#	Cerrar cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "existsConcepto" de "BotServerDAO"')

		return resultado

	def searchConcepto(self, res_preg: str, tipo: str or list=None,
					porc_comp: float=3.0):

		"""Permite realizar una búsqueda inteligente de Conceptos Teóricos,
			usando como algoritmo de comparación la diferencia semántica
			entre las preguntas de los Conceptos Teóricos. Como resultado,
			puede devolver los Datos tipo texto de una o más respuestas de
			conceptos teóricos que se consideren coincidentes

		Parámetros:
		-----------
		res_preg: str
			Resumen de pregunta por el cual se va a realizar la búsqueda

		tipo: str o list de str
			Categoría semántica a la que pertenece el la pregunta cuyo resumen
			de pregunta se ha proporcionado en "res_preg". Introducir
			lista de str si se desea considerar otras categorías semánticas
			auxiliares, donde el primer elemento de la lista es la categoría
			principal

		porc_comp: float
			Ratio usado para calcular el umbral de diferencia máxima permitida
			en función del número de palabras que contenidas en los resúmenes
			comparados. Debe contener un valor comprendido en [0,1]

		Devuelve:
		--------
		OrderedDict con el par id_dato (int) - dato (dict)
			Donde id_dato es el identificador asociado al dato que forma
			parte de la respuesta dada y dato es un diccionario que incluyen
			toda la información sobre el dato.

			En concreto, dato presenta el siguiente formato:

			·tipo_dato: 'texto'
			·texto: str o list str
			 	Texto o textos a almacenar
		"""

		self.__log.debug('Iniciada función "searchConcepto" de "BotServerDAO"')

		#	Comprobar los datos de entrada
		if not isinstance(res_preg, str):
			raise ValueError('"res_preg" debe de ser str')

		if tipo:
			if isinstance(tipo, list):
				for t in tipo:
					if not isinstance(t, str):
						raise ValueError('Algún valor de "tipo" no es str')
			elif isinstance(tipo, str):
				tipo = [tipo]
			else:
				raise ValueError('"tipo" debe de ser str o lista de str')

		if not isinstance(porc_comp, (int, float)):
			raise ValueError('"porc_comp" debe ser float')
		elif porc_comp < 0.0:
			raise ValueError('"porc_comp" debe de ser mayor que 0')

		#	Determinar la diferencia máxima permitida entre las palabras de
		#	res_preg y las cotejadas en la base de datos a partir del
		#	porc_comp establecido, pero el mínimo debe de ser 1
		amplitud = max( int(porc_comp * (res_preg.count(' ')+1)), 1)
		#	Esto podría dar errores

		#	Preparar tipo para iterar sobre él
		if not tipo:
			tipo = [None]
		elif len(tipo) > 2:
			tipo = [[tipo[0]], tipo[1:]]
		else:
			tipo = [tipo]

		#	Tomar cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar consulta
		self.__log.debug('Realizando búsqueda con resumen_pregunta=%s y '\
												'tipo=%s y porc_comp=%f' % (
													res_preg, tipo, porc_comp))
		mutex.acquire()

		#	Respuestas a devolver
		respuestas = OrderedDict()

		for t in tipo:
			if t == None:

				#	No se ha especificado tipo
				consulta = cursor.execute(
				'''SELECT DISTINCT id
					FROM
						(SELECT Concepto.id AS id,
							compare_words(ConceptoPregunta.resumen_pregunta, ?)
											AS score
						FROM Concepto, ConceptoPregunta
						WHERE ConceptoPregunta.id=Concepto.id AND
							score=(SELECT MIN(compare_words(resumen_pregunta,?))
										FROM ConceptoPregunta
										WHERE score <= ?));''',
						(res_preg, res_preg, amplitud))

			else:
				#	Hay un tipo especificado
				consulta = cursor.execute(
				'''SELECT DISTINCT concepto_id
					FROM
						(SELECT Concepto.id AS concepto_id,
							compare_words(ConceptoPregunta.resumen_pregunta,?)
											AS score
						FROM Concepto, ConceptoPregunta
						WHERE ConceptoPregunta.tipo IN %s AND
							ConceptoPregunta.id=Concepto.id AND
							score=(SELECT MIN(compare_words(resumen_pregunta,?))
										FROM ConceptoPregunta
										WHERE tipo IN %s) AND
							score <= ?);'''%((BotServerDAO.__to_sql_tuple(t),)*2),#(tuple(['"'+x+'"' for x in t])*2)
						(res_preg, res_preg, amplitud))

			id_conceptos = BotServerDAO.__to_sql_tuple(consulta.fetchall())

			#	Si no hay conceptos, se salta
			if not id_conceptos:
				continue

			consulta = cursor.execute(
				'''SELECT id, tipo_dato AS "tipo_dato [TIPO_DATOARCHIVO]",
						contenido
					FROM
						(SELECT DatoTexto.id AS id, \'texto\' AS tipo_dato,
							texto AS contenido,
							Dato_Concepto.id_concepto AS id_concepto
						FROM DatoTexto, Dato_Concepto
						WHERE Dato_Concepto.id_concepto IN %s AND
							DatoTexto.id=Dato_Concepto.id_dato
						UNION
						SELECT DatoArchivo.id AS id,
							DatoArchivo.tipo AS tipo_dato,
							ruta_archivo AS contenido,
							Dato_Concepto.id_concepto AS id_concepto
						FROM DatoArchivo, Dato_Concepto, Concepto,
							ConceptoPregunta
						WHERE Dato_Concepto.id_concepto IN %s AND
							DatoArchivo.id=Dato_Concepto.id_dato)
						ORDER BY id;''' % ((id_conceptos,)*2) )

			#	Meter los datos en un diccionario
			for fila in consulta:
				respuestas[fila[0]] = dict(zip(fila.keys()[1:], fila[1:]))


			#	Llegados a este punto, si no se ha encontrado ninguna respuesta,
			#	se prueba con los tipos auxiliares, pero si se ha encontrado
			#	alguna, no interesa consultar los tipos auxiliares
			if respuestas:
				break


		#	Cerrar cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "searchConcepto" de "BotServerDAO"')
		return respuestas if respuestas else None

	def listAllConcepts(self): #Poner otro nombre

		"""Permite obtener la lista entera de Preguntas de los conceptos
			teóricos

		Devuelve:
		---------
		list de str que contiene las preguntas de todos los conceptos teóricos
		"""

		self.__log.debug('Iniciada función "listAllConcepts" de "BotServerDAO"')

		#	Tomar el cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar consulta
		self.__log.debug('Ejecutando consulta')
		mutex.acquire()

		consulta = cursor.execute('SELECT pregunta FROM ConceptoPregunta;')

		resultado = [fila[0] for fila in consulta]

		#	Cerrar el cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "listAllConcepts" de '\
															'"BotServerDAO"')
		return resultado if resultado else None

	def listAllConceptsTextAnswers(self):

		"""Permite obtener la lista entera de Respuestas de todos los conceptos
			teóricos

		Devuelve:
		---------
		list de str que contiene las respuestas de todos los conceptos teóricos
		"""

		self.__log.debug('Iniciada función "listAllConceptsTextAnswers" de '\
															'"BotServerDAO"')

		#	Tomar el cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar consulta
		self.__log.debug('Ejecutando consulta')
		mutex.acquire()

		consulta = cursor.execute('''SELECT texto
										FROM DatoTexto
										WHERE id IN
										(SELECT DISTINCT id_dato
										FROM Dato_Concepto);''')

		resultado = [fila[0] for fila in consulta]

		#	Cerrar el cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "listAllConceptsTextAnswers" de '\
															'"BotServerDAO"')
		return resultado if resultado else None

	def listAllConceptosMultimediaFiles(self):
		return # Eliminar
		self.__log.debug('Iniciada función "listAllConceptosMultimediaFiles" '\
															'de "BotServerDAO"')

		#	Tomar cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Ejecutar la consulta
		self.__log.debug('Realizando consulta')
		mutex.acquire()

		consulta = cursor.execute('''SELECT ruta_archivo
										FROM DatoArchivo
										WHERE id IN
										(SELECT id_dato FROM Dato_Concepto);''')

		resultado = consulta.fetchall()

		#	Cerrar cursor y liberar semáforo
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "listAllConceptosMultimediaFiles"'\
														' de "BotServerDAO"')
		return resultado

	def addDato(self, dato: dict, fecha_creacion: datetime.datetime,
				id_mensaje=None, id_comunicado=None,
				id_concepto=None):

		"""Permite registrar un Dato contenido por un mnesaje, un Comunicado
			o un Concepto. Sólo se debe de especificar uno de los tres

		Parámetros:
		-----------
		dato: dict
			Diccionario que contiene los Datos del Dato a almacenar y que
			almacena los siguientes datos:

			Para tipo texto:

			·tipo_dato: 'texto'
			·texto: str o list str
			 	Texto o textos a almacenar

			Para tipo Multimedia con Archivo:

			·tipo_dato: str
				Tipo de Dato Multimedia almacenado: Puede adoptar los valores
				'imagen', 'audio', 'video'. 'nota_voz', 'nota_video',
				'documento','animacion' y 'sticker'

			·ruta_archivo: str
				Ruta en el sistema de ficheros en la que el servidor ha
				almacenado el Archivo.

			·mime type: str
				Valor del encabezado Mime asociado al archivo
				Parámetro opcional

			·file id: int
				Identificador de archivo asociado por la plataforma de
				mensajerı́a a dicho Archivo.

			·sticker_emoji: str
				emoji asociado al Sticker. Sólo para stickers
				Parámetro opcional

			·sticker_conjunto: str
				Nombre del conjunto al que pertenece el Sticker.
				Sólo para stickers
				Parámetro opcional

			·sticker_tipo: str
				Tipo de sticker, puede adoptar dos valores: normal o animado.
				Sólo para stickers.
				Parámetro opcional
				NOTA: Actualmente en desuso

			Para tipo Contacto:

			·tipo_dato: 'contacto'

			·nombre: str
				Nombre o primer nombre asociado al Contacto.

			·apellidos: str
				Nombre o segundo nombre asociado al Contacto.
				Parámetro opcional

			·telefono: str
				Número de teléfono asociado al Contacto.

			·vcard: str
				Datos recogidos en la vcard asociada al Contacto.
				Parámetro opcional

			·id_usuario: int
				Identificador de usuario asociado por la plataforma de
				mensajerı́a al usuario asociado al Contacto.
				Parámetro opcional

			Para tipo Localizacion y Avenida:

			·tipo_dato: 'localizacion'

			·latitud: int
				Latitud geográfica de la Localizacion o Avenida.

			·longitud: int
				Longitud geográfica de la Localizacion o Avenida

			·titulo: str
				Tı́tulo que recibe la Avenida localizada en la Localizacion.
				Parámetro opcional

			·direccion: str
				Direccion de la avenida localizada en la Localizacion.
				Parámetro opcional

			·id cuadrante: int
				Identificador del cuadrante asociado a la avenida localizada en
				la Localizacion. Parámetro opcional

			·tipo cuadrante: str
				Tipo de cuadrante asociado a la avenida localizada en la
				Localizacion.
				Parámetro opcional

		fecha_creacion: datetime.datetime
			Fecha en la que el dato fue creado

		id_mensaje: int
			Identificador del Mensaje al cual se añaden los Datos

		id_comunicado: int
			Identificador del comunicado al cual se añade el Mensaje

		id_concepto: int
			Identificador del Concepto Teórico al cual se añade el Mensaje
		"""

		if 'tipo_dato' not in dato:
			raise ValueError('Se requiere el campo "tipo_dato" en el '\
														'dato proporcionado')

		if dato['tipo_dato'] == 'texto':
			return self.addDatoTexto(fecha_creacion=fecha_creacion,
										texto=dato['contenido'],
										id_mensaje=id_mensaje,
										id_comunicado=id_comunicado,
										id_concepto=id_concepto)

		elif dato['tipo_dato'] in ('imagen', 'video', 'audio', 'nota_voz',
									'nota_video', 'animacion', 'documento'):

			return self.addDatoArchivo(fecha_creacion=fecha_creacion,
											tipo=dato['tipo_dato'],
											ruta_archivo=dato['contenido'],
											file_id=dato['file_id'],
											mime_type=dato['mime_type'],
											id_mensaje=id_mensaje,
											id_comunicado=id_comunicado,
											id_concepto=id_concepto)

		elif dato['tipo_dato'] == 'sticker':
			return self.addDatoArchivo(fecha_creacion=fecha_creacion,
									tipo=dato['tipo_dato'],
									ruta_archivo=dato['contenido'],
									file_id=dato['file_id'],
									mime_type=dato['mime_type'],
									sticker_emoji=dato['sticker_emoji'],
									sticker_tipo=dato['sticker_tipo'],
									sticker_conjunto=dato['sticker_conjunto'],
									id_mensaje=id_mensaje,
									id_comunicado=id_comunicado,
									id_concepto=id_concepto)

		elif dato['tipo_dato'] == 'localizacion':

			if 'titulo' in dato:

				return self.addDatoLocalizacion(
										fecha_creacion=fecha_creacion,
										longitud=dato['longitud'],
										latitud=dato['latitud'],
										titulo=dato['titulo'],
										direccion=dato['direccion'],
										id_cuadrante=dato['id_cuadrante'],
										tipo_cuadrante=dato['tipo_cuadrante'],
										id_mensaje=id_mensaje,
										id_comunicado=id_comunicado,
										id_concepto=id_concepto)
			else:
				return self.addDatoLocalizacion(
										fecha_creacion=fecha_creacion,
										longitud=dato['longitud'],
										latitud=dato['latitud'],
										id_mensaje=id_mensaje,
										id_comunicado=id_comunicado,
										id_concepto=id_concepto)

		elif dato['tipo_dato'] == 'contacto':
			return self.addDatoContacto(
										fecha_creacion=fecha_creacion,
										telefono=dato['telefono'],
										nombre=dato['nombre'],
										apellidos=dato['apellidos'],
										id_usuario=dato['id_usuario'],
										vcard=dato['vcard'],
										id_mensaje=id_mensaje,
										id_comunicado=id_comunicado,
										id_concepto=id_concepto)

	def addDatoTexto(self, fecha_creacion: datetime.datetime, texto: list or str,
						id_mensaje: int=None, id_comunicado: int=None,
						id_concepto: int=None, use_mutex=True) -> int or list:

		"""Permite registrar uno o más Datos de tipo texto contenido por un
			mensaje, un Comunicado o un Concepto. Sólo se debe de especificar
			uno de los tres.

		Parámetros:
		-----------
		texto: str o list str
			Texto o textos a almacenar

		fecha_creacion: datetime.datetime
			Fecha en la que el dato fue creado

		id_mensaje: int
			Identificador del Mensaje al cual se añaden los Datos

		id_comunicado: int
			Identificador del comunicado al cual se añade el Mensaje

		id_concepto: int
			Identificador del Concepto Teórico al cual se añade el Mensaje

		Devuelve:
			int o list de int
			Identificadores dados a los datos almacenados
		"""

		self.__log.debug('Iniciada función "addDatoTexto" de "BotServerDAO"')

		#	Comprobar y procesar los parámetros de entrada
		if id_mensaje and not isinstance(id_mensaje, int):
			raise ValueError('"id_mensaje" no es int')

		if id_comunicado and not isinstance(id_comunicado, int):
			raise ValueError('"id_comunicado" no es int')

		if id_concepto and not isinstance(id_concepto, int):
			raise ValueError('"id_concepto" no es int')

		if ((id_mensaje is not None and id_comunicado is not None) or
			(id_mensaje is not None and id_concepto is not None) or
		 	(id_comunicado is not None and id_concepto is not None)):
			raise ValueError('Sólo se debe de proporcionar uno de los tres:'\
							' "id_mensaje", "id_comunicado" o "id_concepto"')

		if not isinstance(fecha_creacion, datetime.datetime):
			raise ValueError('"fecha_creacion" debe de ser objeto de'\
													' tipo datetime.datetime')

		if isinstance(texto, list):

			for t in texto:
				if not isinstance(t, str):
					raise ValueError('"texto" contiene algún valor que no es str')

		elif isinstance(texto, str):
			texto = [texto]

		else:
			raise ValueError('"texto" debe de ser str o lista de strs')

		#	Tomar cursor y preparar semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock() if use_mutex else None

		#	Realizar inserciones
		self.__log.debug('Ejecutando inserciones con valores: '\
						'fecha_creacion={}, texto={}, id_mensaje={}, '\
						'id_comunicado={} e id_concepto={}'.format(
						fecha_creacion, texto, id_mensaje, id_comunicado,
																id_concepto))
		if use_mutex: mutex.acquire()

		ids_dato = [] #	Lista de índices de los datos
		for t in texto:

			cursor.execute('INSERT INTO Dato(fecha_creacion) VALUES(?);',
							(fecha_creacion,))
			id_dato = cursor.execute('SELECT last_insert_rowid();').fetchone()[0]
			ids_dato.append(id_dato)

			cursor.execute('INSERT INTO DatoTexto VALUES (?,?);', (id_dato, t))

			if id_mensaje:
				cursor.execute('INSERT INTO Dato_Mensaje VALUES(?,?);',
								(id_dato, id_mensaje))
			elif id_comunicado:
				cursor.execute('INSERT INTO Dato_Comunicado VALUES(?,?);',
								(id_dato, id_comunicado))
			else:
				cursor.execute('INSERT INTO Dato_Concepto VALUES(?,?);',
								(id_dato, id_concepto))

		#	Realizar el commit
		self.__con_bd.commit()

		#	Cerrar el cursor y liberar semáforo
		cursor.close()
		if use_mutex: mutex.release()

		self.__log.debug('Finalizada función "addDatoTexto" de "BotServerDAO"')
		return ids_dato if len(ids_dato) > 1 else ids_dato[0]

	def addDatoArchivo(self, fecha_creacion: datetime.datetime,
									tipo: str,
									ruta_archivo=None,
									file_id=None,
									mime_type=None,
									sticker_emoji=None,
									sticker_conjunto=None,
									sticker_tipo=None,
									id_mensaje=None,
									id_comunicado=None,
									id_concepto=None,
									use_mutex=True) -> int:

		"""Permite registrar un Dato de tipo multimedia con un archivo
			asociado contenido por un mensaje, un Comunicado o un Concepto.
			Sólo se debe de especificar uno de los tres, del mismo modo,
			se debe de aportar, bien una ruta_archivo o bien un file_id

			Nota: En esta versión no se ha implementado la posibilidad de que un
			Concepto Teórico almacene este tipo de Dato, por lo que no tiene
			ningún sentido asociar un archivo Multimedia a un Contenido teórico

		Parámetros:
		-----------

		fecha_creacion: datetime.datetime
			Fecha en la que el dato fue creado

		tipo: str
			Tipo de Dato Multimedia almacenado: Puede adoptar los valores
			'imagen', 'audio', 'video'. 'nota_voz', 'nota_video', 'documento',
			'animacion' y 'sticker'

		ruta_archivo: str
			Ruta en el sistema de ficheros en la que el servidor ha
			almacenado el Archivo.

		mime type: str
			Valor del encabezado Mime asociado al archivo
			Parámetro opcional

		file id: int
			Identificador de archivo asociado por la plataforma de
			mensajerı́a a dicho Archivo.

		sticker_emoji: str
			emoji asociado al Sticker. Sólo para stickers
			Parámetro opcional

		sticker_conjunto: str
			Nombre del conjunto al que pertenece el Sticker. Sólo para stickers
			Parámetro opcional

		sticker_tipo: str
			Tipo de sticker, puede adoptar dos valores: normal o animado.
			Sólo para stickers.
			Parámetro opcional
			NOTA: Actualmente en desuso

		id_mensaje: int
			Identificador del Mensaje al cual se añaden los Datos

		id_comunicado: int
			Identificador del comunicado al cual se añade el Mensaje

		id_concepto: int
			Identificador del Concepto Teórico al cual se añade el Mensaje

		use_mutex: bool por efecto True
			Indica si se desean usar mutex para proteger las operaciones de
			inserción en la base de datos

		Devuelve:
			int: Identificador dado al dato almacenado
		"""

		self.__log.debug('Iniciada función "addDatoArchivo" de'\
															' "BotServerDAO"')

		#	Comprobar y procesar los parámetros de entrada
		if id_mensaje is not None and not isinstance(id_mensaje, int):
			raise ValueError('"id_mensaje" no es int')

		if id_comunicado is not None and not isinstance(id_comunicado, int):
			raise ValueError('"id_comunicado" no es int')

		if id_concepto is not None and not isinstance(id_concepto, int):
			raise ValueError('"id_concepto" no es int')

		if ((id_mensaje is not None and id_comunicado is not None) or
			(id_mensaje is not None and id_concepto is not None) or
		 	(id_comunicado is not None and id_concepto is not None)):
			raise ValueError('Sólo se debe de proporcionar uno de los tres:'\
							' "id_mensaje", "id_comunicado" o "id_concepto"')

		if not isinstance(fecha_creacion, datetime.datetime):
			raise ValueError('"fecha_creacion" debe de ser objeto de'\
													' tipo datetime.datetime')

		if not isinstance(tipo, str):
			raise ValueError('"tipo" debe de ser str')
		elif tipo == 'sticker' and (not sticker_conjunto or not sticker_tipo):
			raise valueError('Para los stickers, los campos sticker_conjunto'\
											' y sticker_tipo son requeridos')
		else:
			#	Obtener valor asociado al TIPO_DATOARCHIVO
			try:
				tipo = BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO'][tipo]
			except:
				raise ValueError('"%s" no es un tipo válido' % tipo)

			#	Obtener valor asociado al TIPO_STICKER
			if tipo == 'sticker':
				try:
					sticker_tipo = (BotServerDAO.__BD_TIPOS['TIPO_STICKER']
																[sticker_tipo])
				except:
					raise ValueError(('"%s" no es un tipo de sticker válido' %
																sticker_tipo))

		if ruta_archivo and not isinstance(ruta_archivo, str):
			raise ValueError('"ruta_archivo" debe de ser str')

		if mime_type and not isinstance(mime_type, str):
			raise ValueError('"mime_type" debe de ser str')

		if file_id and not isinstance(file_id, str):
			raise ValueError('"file_id" no es str')

		if not ruta_archivo and not file_id:
			raise ValueError('Se debe proporcionar alguno/s de los valores:'\
													' ruta_archivo y/o file_id')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock() if use_mutex else None

		#	Realizar inserciones
		self.__log.debug('Insertando valores: fecha_creacion={}, tipo={}, '\
							'ruta_archivo={}, file_id={}, mime_type={}, '\
							'sticker_emoji={}, sticker_conjunto={}, '\
							'sticker_tipo={}, id_mensaje={}, id_comunicado={},'\
							' id_concepto={}'.format(fecha_creacion, tipo,
							ruta_archivo, file_id, mime_type, sticker_emoji,
							sticker_conjunto, sticker_tipo, id_mensaje,
							id_comunicado, id_concepto))
		if use_mutex: mutex.acquire()

		cursor.execute('INSERT INTO Dato(fecha_creacion) VALUES(?);',
						(fecha_creacion,))
		id_dato = cursor.execute('SELECT last_insert_rowid();').fetchone()[0]

		cursor.execute('INSERT INTO DatoArchivo VALUES (?,?,?,?,?);',
						(id_dato, tipo, ruta_archivo, file_id, mime_type))
		if id_mensaje:
			cursor.execute('INSERT INTO Dato_Mensaje VALUES(?,?);',
							(id_dato, id_mensaje))
		elif id_comunicado:
			cursor.execute('INSERT INTO Dato_Comunicado VALUES(?,?);',
							(id_dato, id_comunicado))
		else:
			cursor.execute('INSERT INTO Dato_Concepto VALUES(?,?);',
							(id_dato, id_concepto))

		if tipo == BotServerDAO.__BD_TIPOS['TIPO_DATOARCHIVO']['sticker']:
			if sticker_tipo:
				cursor.execute('''INSERT INTO DatoArchivoSticker
									VALUES(?,?,?,?);''',
					(id_dato, sticker_emoji, sticker_conjunto, sticker_tipo))
			else:
				cursor.execute('''INSERT INTO
									DatoArchivoSticker(id, emoji, conjunto)
									VALUES(?,?,?);''',
						(id_dato, sticker_emoji, sticker_conjunto))

		#	Realizar el commit
		self.__con_bd.commit()

		#	Liberar semáforo y cerrar el cursor
		if use_mutex: mutex.release()
		cursor.close()

		self.__log.debug('Finalizada función "addDatoArchivo" de '\
															'"BotServerDAO"')
		return id_dato

	def addDatoContacto(self, fecha_creacion: datetime.datetime,
									telefono: str,
									nombre: str,
									apellidos: str=None,
									id_usuario: int=None,
									vcard: str=None,
									id_mensaje: int=None,
									id_comunicado: int=None,
									id_concepto: int=None,
									use_mutex=True) -> int:

		"""Permite registrar uno o más Datos de tipo Contacto contenido por un
			mensaje, un Comunicado o un Concepto. Sólo se debe de especificar
			uno de los tres.

			Nota: En esta versión no se ha implementado la posibilidad de que un
			Concepto Teórico almacene este tipo de Dato, por lo que no tiene
			ningún sentido asociar un Contacto a un Contenido teórico

		Parámetros:
		-----------

		fecha_creacion: datetime.datetime
			Fecha en la que el dato fue creado

		nombre: str
			Nombre o primer nombre asociado al Contacto.

		apellidos: str
			Nombre o segundo nombre asociado al Contacto.
			Parámetro opcional

		telefono: str
			Número de teléfono asociado al Contacto.

		vcard: str
			Datos recogidos en la vcard asociada al Contacto.
			Parámetro opcional

		id_usuario: int
			Identificador de usuario asociado por la plataforma de mensajerı́a al
			usuario asociado al Contacto.
			Parámetro opcional

		id_mensaje: int
			Identificador del Mensaje al cual se añaden los Datos

		id_comunicado: int
			Identificador del comunicado al cual se añade el Mensaje

		id_concepto: int
			Identificador del Concepto Teórico al cual se añade el Mensaje

		use_mutex: bool por efecto True
			Indica si se desean usar mutex para proteger las operaciones de
			inserción en la base de datos

		Devuelve:
			int: Identificador dado al dato almacenado
		"""

		self.__log.debug('Iniciada función "addDatoContacto" de "BotServerDAO"')

		#	Comprobar y procesar los parámetros de entrada
		nombres_campos = []
		campos = []
		datos = []

		#	Comprobar y procesar los parámetros de entrada
		if id_mensaje is not None and not isinstance(id_mensaje, int):
			raise ValueError('"id_mensaje" no es int')

		if id_comunicado is not None and not isinstance(id_comunicado, int):
			raise ValueError('"id_comunicado" no es int')

		if id_concepto is not None and not isinstance(id_concepto, int):
			raise ValueError('"id_concepto" no es int')

		if not isinstance(fecha_creacion, datetime.datetime):
			raise ValueError('"fecha_creacion" debe de ser objeto de tipo'\
														' datetime.datetime')

		if not isinstance(telefono, str):
			raise ValueError('"telefono" no es str')
		else:
			nombres_campos.append('telefono')
			datos.append(telefono)
			campos.append('?')

		if not isinstance(nombre, str):
			raise ValueError('"nombre" no es str')
		else:
			datos.append(nombre)
			campos.append('?')
			nombres_campos.append('nombre')

		if apellidos:
			if not isinstance(apellidos, str):
				raise ValueError('"apellidos" no es str')
			else:
				datos.append(apellidos)
				campos.append('?')
				nombres_campos.append('apellidos')

		if id_usuario:
			if not isinstance(id_usuario, int):
				raise ValueError('"id_usuario" no es int')
			else:
				datos.append(id_usuario)
				campos.append('?')
				nombres_campos.append('id_usuario')

		if vcard:
			if not isinstance(vcard, str):
				raise ValueError('"vcard" no es str')
			else:
				datos.append(vcard)
				campos.append('?')
				nombres_campos.append('vcard')

		if ((id_mensaje is not None and id_comunicado is not None) or
			(id_mensaje is not None and id_concepto is not None) or
		 	(id_comunicado is not None and id_concepto is not None)):
			raise ValueError('Sólo se debe de proporcionar uno de los tres:'\
							' "id_mensaje", "id_comunicado" o "id_concepto"')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock() if use_mutex else None

		#	Realizar inserciones
		self.__log.debug('Insertando valores: fecha_creacion={}, telefono={},'\
						' nombre={}, apellidos={}, id_usuario={}, vcard={}, '\
					'id_mensaje={}, id_comunicado={}, id_concepto={}'.format(
							fecha_creacion, telefono, nombre,
							apellidos, id_usuario, vcard, id_mensaje,
							id_comunicado, id_concepto))

		if use_mutex: mutex.acquire()

		cursor.execute('INSERT INTO Dato(fecha_creacion) VALUES(?);',
						(fecha_creacion,))
		id_dato = cursor.execute('SELECT last_insert_rowid();').fetchone()[0]

		#	Añadir el id
		nombres_campos.insert(0, 'id')
		campos.append('?')
		datos.insert(0, id_dato)

		cursor.execute('INSERT INTO DatoContacto(%s) VALUES (%s);'%
									(','.join(nombres_campos), ','.join(campos)),
									tuple(datos))

		if id_mensaje is not None:
			cursor.execute('INSERT INTO Dato_Mensaje VALUES(?,?);',
							(id_dato, id_mensaje))
		elif id_comunicado is not None:
			cursor.execute('INSERT INTO Dato_Comunicado VALUES(?,?);',
							(id_dato, id_comunicado))
		else:
			cursor.execute('INSERT INTO Dato_Concepto VALUES(?,?);',
							(id_dato, id_concepto))

		#	Realizar el commit
		self.__con_bd.commit()

		#	Liberar semáforo y cerrar el cursor
		if use_mutex: mutex.release()
		cursor.close()

		self.__log.debug('Finalizada función "addDatoContacto" de'\
															' "BotServerDAO"')
		return id_dato

	def addDatoLocalizacion(self, fecha_creacion: datetime.datetime,
									longitud: int,
									latitud: int,
									titulo=None,
									direccion=None,
									id_cuadrante=None,
									tipo_cuadrante=None,
									id_mensaje=None,
									id_comunicado=None,
									id_concepto=None,
									use_mutex=True) -> int:

		"""Permite registrar uno o más Datos de tipo Localizacion, que se
			correesponden con Localizaciones y Avenidas enviadas por medio de
			la plataforma contenidos por un
			mensaje, un Comunicado o un Concepto. Sólo se debe de especificar
			uno de los tres.

			Nota: En esta versión no se ha implementado la posibilidad de que un
			Concepto Teórico almacene este tipo de Dato, por lo que no tiene
			ningún sentido asociar un Contacto a un Contenido teórico

		Parámetros:
		-----------

		fecha_creacion: datetime.datetime
			Fecha en la que el dato fue creado

		latitud: int
			Latitud geográfica de la Localizacion o Avenida.

		longitud: int
			Longitud geográfica de la Localizacion o Avenida

		titulo: str
			Tı́tulo que recibe la Avenida localizada en la Localizacion.
			Parámetro opcional

		direccion: str
			Direccion de la avenida localizada en la Localizacion.
			Parámetro opcional

		id cuadrante: int
			Identificador del cuadrante asociado a la avenida localizada en la
			Localizacion. Parámetro opcional

		tipo cuadrante: str
			Tipo de cuadrante asociado a la avenida localizada en la
			Localizacion.
			Parámetro opcional

		id_mensaje: int
			Identificador del Mensaje al cual se añaden los Datos

		id_comunicado: int
			Identificador del comunicado al cual se añade el Mensaje

		id_concepto: int
			Identificador del Concepto Teórico al cual se añade el Mensaje

		use_mutex: bool por efecto True
			Indica si se desean usar mutex para proteger las operaciones de
			inserción en la base de datos

		Devuelve:
			int: Identificador dado al dato almacenado
		"""

		self.__log.debug('Iniciada función "addDatoLocalizacion" de'\
															' "BotServerDAO"')

		#	Comprobar y procesar los parámetros de entrada
		nombres_campos = []
		campos = []
		datos = []

		#	Comprobar y procesar los parámetros de entrada
		if id_mensaje is not None and not isinstance(id_mensaje, int):
			raise ValueError('"id_mensaje" no es int')

		if id_comunicado is not None and not isinstance(id_comunicado, int):
			raise ValueError('"id_comunicado" no es int')

		if id_concepto is not None and not isinstance(id_concepto, int):
			raise ValueError('"id_concepto" no es int')

		if not isinstance(fecha_creacion, datetime.datetime):
			raise ValueError('"fecha_creacion" debe de ser objeto de tipo'\
														' datetime.datetime')

		if not isinstance(longitud, float):
			raise ValueError('"longitud" no es float')
		else:
			datos.append(longitud)
			nombres_campos.append('longitud')
			campos.append('?')

		if not isinstance(latitud, float):
			raise ValueError('"latitud" no es float')
		else:
			datos.append(latitud)
			nombres_campos.append('latitud')
			campos.append('?')

		if titulo:
			if not isinstance(titulo, str):
				raise ValueError('"titulo" no es str')
			else:
				datos.append(titulo)
				nombres_campos.append('titulo')
				campos.append('?')

		if direccion:
			if not isinstance(direccion, str):
				raise ValueError('"direccion" no es str')
			else:
				datos.append(direccion)
				nombres_campos.append('direccion')
				campos.append('?')

		if id_cuadrante:
			if not isinstance(id_cuadrante, str):
				raise ValueError('"id_cuadrante" no es str')
			else:
				datos.append(id_cuadrante)
				nombres_campos.append('id_cuadrante')
				campos.append('?')

		if tipo_cuadrante:
			if not isinstance(tipo_cuadrante, str):
				raise ValueError('"tipo_cuadrante" no es str')
			else:
				datos.append(tipo_cuadrante)
				nombres_campos.append('tipo_cuadrante')
				campos.append('?')

		if ((id_mensaje is not None and id_comunicado is not None) or
			(id_mensaje is not None and id_concepto is not None) or
		 	(id_comunicado is not None and id_concepto is not None)):
			raise ValueError('Sólo se debe de proporcionar uno de los tres:'\
							' "id_mensaje", "id_comunicado" o "id_concepto"')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock() if use_mutex else None

		#	Realizar inserciones
		self.__log.debug('Insertando valores: fecha_creacion={}, longitud={},'\
						' latitud={}, titulo={}, direccion={}, '\
						'id_cuadrante={}, tipo_cuadrante={}, id_mensaje={},'\
						' id_comunicado={}, id_concepto={}'.format(
						fecha_creacion, longitud, latitud, titulo, direccion,
						id_cuadrante, tipo_cuadrante, id_mensaje,
						id_comunicado, id_concepto))

		if use_mutex: mutex.acquire()

		cursor.execute('INSERT INTO Dato(fecha_creacion) VALUES(?);',
						(fecha_creacion,))
		id_dato = cursor.execute('SELECT last_insert_rowid();').fetchone()[0]

		#	Añadir el id
		nombres_campos.insert(0, 'id')
		campos.append('?')
		datos.insert(0, id_dato)

		cursor.execute(('INSERT INTO DatoLocalizacion(%s) VALUES(%s);' %
							(','.join(nombres_campos), ','.join(campos))),
							tuple(datos))

		if id_mensaje is not None:
			cursor.execute('INSERT INTO Dato_Mensaje VALUES(?,?);',
							(id_dato, id_mensaje))
		elif id_comunicado is not None:
			cursor.execute('INSERT INTO Dato_Comunicado VALUES(?,?);',
							(id_dato, id_comunicado))
		else:
			cursor.execute('INSERT INTO Dato_Concepto VALUES(?,?);',
							(id_dato, id_concepto))

		#	Realizar el commit
		self.__con_bd.commit()

		#	Liberar semáforo y cerrar el cursor
		if use_mutex: mutex.release()
		cursor.close()

		self.__log.debug('Finalizada función "addDatoLocalizacion" de'\
															' "BotServerDAO"')
		return id_dato

	def editDatoArchivo(self, id_dato: int,
									fecha_creacion: datetime.datetime=None,
									ruta_archivo: str=None,
									file_id: int=None,
									mime_type: str=None,
									sticker_emoji: str=None,
									sticker_conjunto: str=None,
									sticker_tipo: str=None) -> int:

		"""Permite editar un Dato de tipo multimedia con un archivo
			existente en la base de datos e identificado por su identificador
			asociado en la base de datos.
			Se debe de proporcionar únciamente los parámetros que se deseen
			editar en el DatoArchivo

		Parámetros:
		-----------

		fecha_creacion: datetime.datetime
			Fecha en la que el dato fue creado

		tipo: str
			Tipo de Dato Multimedia almacenado: Puede adoptar los valores
			'imagen', 'audio', 'video'. 'nota_voz', 'nota_video', 'documento',
			'animacion' y 'sticker'

		ruta_archivo: str
			Ruta en el sistema de ficheros en la que el servidor ha
			almacenado el Archivo.

		mime type: str
			Valor del encabezado Mime asociado al archivo

		file id: int
			Identificador de archivo asociado por la plataforma de
			mensajerı́a a dicho Archivo.

		sticker_emoji: str
			emoji asociado al Sticker. Sólo para stickers

		sticker_conjunto: str
			Nombre del conjunto al que pertenece el Sticker. Sólo para stickers

		sticker_tipo: str
			Tipo de sticker, puede adoptar dos valores: normal o animado.
			Sólo para stickers.
			NOTA: Actualmente en desuso

		id_mensaje: int
			Identificador del Mensaje al cual se añaden los Datos

		id_comunicado: int
			Identificador del comunicado al cual se añade el Mensaje

		id_concepto: int
			Identificador del Concepto Teórico al cual se añade el Mensaje

		use_mutex: bool por defecto True
			Indica si se desean usar mutex para proteger las operaciones de
			inserción en la base de datos

		Devuelve:
			int: Identificador dado al dato almacenado
		"""

		self.__log.debug('Iniciada función "editDatoArchivo" de '\
															'"BotServerDAO"')

		datos = []
		campos=''

		#	Comprobar y procesar los parámetros de entrada
		if not isinstance(id_dato, int):
			raise ValueError('"id_dato" no es int')

		if fecha_creacion:
			if not isinstance(fecha_creacion, datetime.datetime):
				raise ValueError('"fecha_creacion" debe de ser objeto de '\
													'tipo datetime.datetime')
			else:
				datos.append(fecha_creacion)
				campos += 'fecha_creacion=?,'

		if ruta_archivo:
			if not isinstance(ruta_archivo, str):
				raise ValueError('"ruta_archivo" debe de ser str')
			else:
				datos.append(ruta_archivo)
				campos += 'ruta_archivo=?,'

		if mime_type:
			if not isinstance(mime_type, str):
				raise ValueError('"mime_type" debe de ser str')
			else:
				datos.append(mime_type)
				campos += 'mime_type=?,'

		if file_id is not None:
			if not isinstance(file_id, int):
				raise ValueError('"file_id" no es int')
			else:
				datos.append(file_id)
				campos += 'file_id=?,'

		if datos:
			campos = campos[:-1] #	Borrar coma sobrante
			datos.append(id_dato)		 #	Añadir id_dato
		else:
			raise ValueError('Al menos un parámetro se debe proporcionar')

		#	Tomar cursor y semáforo
		cursor = self.__con_bd.cursor()
		mutex = Lock()

		#	Realizar modificaciones
		self.__log.debug('Editando Dato Multimedia con id={} con los '\
							'siguientes valores: fecha_creacion={}, tipo={},'\
							' ruta_archivo={}, file_id={}, mime_type={},'\
							' sticker_emoji={}, sticker_tipo={} y'\
							' sticker_conjunto={}'.format(id_dato,
							fecha_creacion, tipo, ruta_archivo, file_id,
							mime_type, sticker_emoji, sticker_tipo,
							sticker_conjunto))
		mutex.acquire()

		cursor.execute('UPDATE DatoArchivo SET %s WHERE id_dato=? ' % campos,
						tuple(datos))

		#	Realizar commit
		self.__con_bd.commit()

		#	Liberar semáforo y cerrar cursor
		cursor.close()
		mutex.release()

		self.__log.debug('Finalizada función "editDatoArchivo" de'\
															' "BotServerDAO"')

	def __del__(self):
		#	Cerrar la conexión con la BD y destruirlo
		if self.__con_bd:
			self.__con_bd.rollback()
			self.__con_bd.close()
			del self.__con_bd
