###############################################################################
# Descripción: Clase manejadora del evento producido cuando el bot es agregado
#				a un grupo
# Autor: Nicolás Cubero Torres
###############################################################################

#	Módulos importados
from telegram.ext.handler import Handler
from telegram import Update

class EnteringGroupHandler(Handler):

	"""
	Clase manejadora del evento producido al agregar el bot a un grupo
	o supergrupo

	"""

	def __init__(self, callback, pass_update_queue=False, pass_job_queue=False,
				 pass_user_data=False, pass_chat_data=False):

		#	Contructor de la clase base
		super(EnteringGroupHandler, self).__init__(
			callback,
			pass_update_queue=pass_update_queue,
			pass_job_queue=pass_job_queue,
			pass_user_data=pass_user_data,
			pass_chat_data=pass_chat_data)


	def check_update(self, update):

		"""
		Permite detectar el hecho de que un bot sea agregado a un grupo o
		supergrupo

		Argumentos:
		-----------
			update: (:class:`telegram.Update`): Nueva actualización telegram

		Devuelve:
		---------
			:obj: bool
		"""

		if (isinstance(update, Update)) and (update.message or
														update.edited_message):

			mensaje = update.message or update.edited_message

			#	Se comprueba que el bot haya sido agregado a un nuevo grupo
			bot = mensaje.bot

			#	El bot ha sido agregado a un nuevo grupo
			if (hasattr(mensaje, 'new_chat_members') and
									bot.get_me() in mensaje.new_chat_members):
				return True

		return False

	def handle_update(self, update, dispatcher):

		"""
		Envía la actualización a :attr:`callback`.

		Parámetros:
			update (:class:`telegram.Update`):
												Actualización Telegram entrante.
			dispatcher (:class:`telegram.ext.Dispatcher`):
												Dispatcher del Update original.
		"""
		optional_args = self.collect_optional_args(dispatcher, update)

		message = update.message or update.edited_message

		return self.callback(dispatcher.bot, update, **optional_args)
