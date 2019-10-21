###############################################################################
# Descripción: Clase manejadora del evento producido cuando el bot es expulsadp
#				a un grupo
# Autor: Nicolás Cubero Torres
###############################################################################

#	Módulos importados
from telegram.ext.handler import Handler
from telegram import Update

class LefteringGroupHandler(Handler):

	"""
	Clase manejadora del evento producido al expulsar el bot de un grupo
	o supergrupo

	Atributos:
	----------
	"""

	def __init__(self, callback, pass_update_queue=False, pass_job_queue=False,
				pass_user_data=False, pass_chat_data=False):

		#	Contructor de la clase base
		super(LefteringGroupHandler, self).__init__(
			callback,
			pass_update_queue=pass_update_queue,
			pass_job_queue=pass_job_queue,
			pass_user_data=pass_user_data,
			pass_chat_data=pass_chat_data)


	def check_update(self, update):

		"""
		Permite detectar el hecho de que un bot sea expulsado de un grupo o
		supergrupo

		Argumentos:
		-----------
			update: (:class:`telegram.Update`): Nueva actualización telegram

		Devuelve:
		---------
			:obj: bool
		"""

		if (isinstance(update, Update) and
				(update.message or update.edited_message)):

			mensaje = update.message or update.edited_message

			if not hasattr(mensaje, 'bot'):
				return False

			#	Se comprueba que el bot haya sido expulsado de un foro
			bot = mensaje.bot

			#	El bot ha sido expulsado de un grupo
			return (hasattr(mensaje, 'left_chat_member') and
						mensaje.left_chat_member and
							bot.get_me() == mensaje.left_chat_member)

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
