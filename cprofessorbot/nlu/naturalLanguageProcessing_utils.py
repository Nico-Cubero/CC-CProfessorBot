################################################################################
# Nombre: naturalLanguageProcessing_utils.py
# Descripción: Módulo con diversas funciones útiles para el procesamiento del
#			   lenguaje natural en idioma castellano
# Autor: Nicolás Cubero Torres
################################################################################

#Enlaces de interés
# https://medium.com/@datamonsters/text-preprocessing-in-python-steps-tools-and-examples-bf025f872908
#https://likegeeks.com/es/tutorial-de-nlp-con-python-nltk/ como usar nltk (tutorial básico)
# https://es.wikipedia.org/wiki/Categor%C3%ADa:Nombres_masculinos Compilación de nombres masculinos no ambiguos de wikipedia
# https://es.wikipedia.org/w/index.php?title=Categor%C3%ADa:Nombres_femeninos&pageuntil=Erika#mw-pages Compilación de nombres femeninos no ambiguos de wikipedia


#   Módulos importados
import datetime
import string
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from nltk.stem import PorterStemmer

#   Revisar
__stemmer = SnowballStemmer('spanish')

#	Recopilación de palabras de parada (stopwords) provenientes de la librería
#	para el procesamiento natural nltk (https://www.nltk.org/ 17 de julio de 2019)
#	Puede ser importada haciendo lo siguiente:
#
#	from nltk.corpus import stopwords
#	palabras_parada = stopwords.words('spanish')
#
#	De la anterior lista proporcionada por este módulo, se toman las siguientes
#	palabras conformando una versión reducida
red_sp_stopwords = set(['de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del',
'se', 'las', 'por', 'un', 'para', 'con', 'una', 'su', 'al', 'lo', 'como',
'más', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'sí', 'porque', 'esta', 'entre',
'cuando', 'muy', 'sobre', 'también', 'me', 'hay', 'donde',
'quien', 'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni',
'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'antes',
'algunos', 'qué', 'unos', 'yo', 'otro', 'otras', 'otra', 'tanto', 'esa',
'estos', 'mucho', 'quienes', 'muchos', 'cual', 'poco', 'ella', 'estar',
'estas', 'algunas', 'algo', 'nosotros', 'mi', 'mis', 'te', 'ti', 'tu',
'tus', 'ellas', 'nosotras', 'vosotros', 'vosotras', 'os', 'tuyo', 'tuya',
'tuyos', 'tuyas', 'suyo', 'suya', 'suyos', 'suyas',
'nuestro', 'nuestra', 'nuestros', 'nuestras', 'vuestro', 'vuestra', 'vuestros',
'vuestras', 'esos', 'esas', 'estoy', 'estamos',
'estemos', 'estaremos', 'estaba', 'estabas',
'estabais', 'estaban', 'estuve', 'estuviste', 'estuvo', 'estuvimos',
'estuvisteis', 'estuvieron', 'estuviera', 'estuvieras',
'estuvierais', 'estuvieran', 'estuviese', 'estuvieses',
'estuvieseis', 'estuviesen', 'estando',
'estadas', 'estad', 'he', 'has', 'ha', 'hemos', 'habéis', 'han', 'haya',
'hayas', 'hayamos', 'hayan', 'habremos', 'hube', 'hubiste', 'hubo',
'hubimos', 'hubisteis', 'hubieron', 'hubiera', 'hubieras'
'hubierais', 'hubieran', 'hubiese', 'hubieses', 'hubieseis',
'hubiesen', 'habiendo', 'habido', 'habida', 'habidos', 'habidas', 'soy',
'eres', 'es', 'somos', 'sois', 'son', 'sea', 'seas', 'seamos',
'sean', 'seremos', 'era', 'eras', 'erais',
'eran', 'fui', 'fuiste', 'fue', 'fuimos', 'fuisteis', 'fueron', 'fuera',
'fueras', 'fuerais', 'fueran', 'fuese', 'fueses',
'fueseis', 'fuesen', 'sintiendo',
'siente', 'sentid', 'tengo', 'tienes', 'tiene', 'tenemos', 'tienen',
'tenga', 'tengas', 'tengamos', 'tengan', 'tendremos',
'tuve', 'tuviste', 'tuvo', 'tuvimos', 'tuvisteis',
'tuvieron', 'tuviera', 'tuvieras', 'tuvierais', 'tuvieran',
'tuviese', 'tuvieses', 'tuvieseis', 'tuviesen', 'teniendo',
'tenido', 'tenida', 'tenidos', 'tenidas', 'tened',

'mas', 'si', 'tambien', 'que', 'el', 'mio', 'mia', 'mios', 'mias', 'estas',
'estais', 'estan', 'este', 'estes',  'esteis', 'esten', 'estare', 'estaras',
'estara', 'estareis', 'estaran', 'estaria', 'estarias', 'estariamos',
'estariais', 'estarian', 'estabamos', 'estuvieramos', 'estuviesemos', 'habeis',
'hayais', 'habreis', 'habran', 'habria', 'habrias', 'habriamos', 'habriais',
'habrian', 'habia', 'habias', 'habiamos', 'habiais', 'habian', 'hubiesemos',
'seais', 'sere', 'seras', 'sera', 'sereis', 'seran', 'seria', 'serias',
'seriamos', 'seriais', 'serian', 'eramos', 'fueramos', 'fuesemos', 'teneis',
'tengais', 'tendre', 'tendras', 'tendreis', 'tendran', 'tendria', 'tendrias',
'tendriamos', 'tendriais', 'tendrian', 'tenia', 'tenias', 'teniamos', 'teniais',
'tenian', 'tuvieramos', 'tuviesemos'])
#	Por otra parte, se toma la lista completa de este módulo de nltk a la cual
#	se añaden todas las palabras de la lista que llevan tilde pero removiéndola
#	con el fin de considerar como palabras de parada las palabras con tilde
#	que hayan sido escritas sin tilde por parte de los usuarios
full_sp_stopwords = set(['de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del',
'se', 'las', 'por', 'un', 'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'como',
'más', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'sí', 'porque', 'esta', 'entre',
'cuando', 'muy', 'sin', 'sobre', 'también', 'me', 'hasta', 'hay', 'donde',
'quien', 'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni',
'contra', 'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'mí', 'antes',
'algunos', 'qué', 'unos', 'yo', 'otro', 'otras', 'otra', 'él', 'tanto', 'esa',
'estos', 'mucho', 'quienes', 'nada', 'muchos', 'cual', 'poco', 'ella', 'estar',
'estas', 'algunas', 'algo', 'nosotros', 'mi', 'mis', 'tú', 'te', 'ti', 'tu',
'tus', 'ellas', 'nosotras', 'vosotros', 'vosotras', 'os', 'mío', 'mía', 'míos',
'mías', 'tuyo', 'tuya', 'tuyos', 'tuyas', 'suyo', 'suya', 'suyos', 'suyas',
'nuestro', 'nuestra', 'nuestros', 'nuestras', 'vuestro', 'vuestra', 'vuestros',
'vuestras', 'esos', 'esas', 'estoy', 'estás', 'está', 'estamos', 'estáis',
'están', 'esté', 'estés', 'estemos', 'estéis', 'estén', 'estaré', 'estarás',
'estará', 'estaremos', 'estaréis', 'estarán', 'estaría', 'estarías',
'estaríamos', 'estaríais', 'estarían', 'estaba', 'estabas', 'estábamos',
'estabais', 'estaban', 'estuve', 'estuviste', 'estuvo', 'estuvimos',
'estuvisteis', 'estuvieron', 'estuviera', 'estuvieras', 'estuviéramos',
'estuvierais', 'estuvieran', 'estuviese', 'estuvieses', 'estuviésemos',
'estuvieseis', 'estuviesen', 'estando', 'estado', 'estada', 'estados',
'estadas', 'estad', 'he', 'has', 'ha', 'hemos', 'habéis', 'han', 'haya',
'hayas', 'hayamos', 'hayáis', 'hayan', 'habré', 'habrás', 'habrá', 'habremos',
'habréis', 'habrán', 'habría', 'habrías', 'habríamos', 'habríais', 'habrían',
'había', 'habías', 'habíamos', 'habíais', 'habían', 'hube', 'hubiste', 'hubo',
'hubimos', 'hubisteis', 'hubieron', 'hubiera', 'hubieras', 'hubiéramos',
'hubierais', 'hubieran', 'hubiese', 'hubieses', 'hubiésemos', 'hubieseis',
'hubiesen', 'habiendo', 'habido', 'habida', 'habidos', 'habidas', 'soy',
'eres', 'es', 'somos', 'sois', 'son', 'sea', 'seas', 'seamos', 'seáis',
'sean', 'seré', 'serás', 'será', 'seremos', 'seréis', 'serán', 'sería',
'serías', 'seríamos', 'seríais', 'serían', 'era', 'eras', 'éramos', 'erais',
'eran', 'fui', 'fuiste', 'fue', 'fuimos', 'fuisteis', 'fueron', 'fuera',
'fueras', 'fuéramos', 'fuerais', 'fueran', 'fuese', 'fueses', 'fuésemos',
'fueseis', 'fuesen', 'sintiendo', 'sentido', 'sentida', 'sentidos', 'sentidas',
'siente', 'sentid', 'tengo', 'tienes', 'tiene', 'tenemos', 'tenéis', 'tienen',
'tenga', 'tengas', 'tengamos', 'tengáis', 'tengan', 'tendré', 'tendrás',
'tendrá', 'tendremos', 'tendréis', 'tendrán', 'tendría', 'tendrías',
'tendríamos', 'tendríais', 'tendrían', 'tenía', 'tenías', 'teníamos',
'teníais', 'tenían', 'tuve', 'tuviste', 'tuvo', 'tuvimos', 'tuvisteis',
'tuvieron', 'tuviera', 'tuvieras', 'tuviéramos', 'tuvierais', 'tuvieran',
'tuviese', 'tuvieses', 'tuviésemos', 'tuvieseis', 'tuviesen', 'teniendo',
'tenido', 'tenida', 'tenidos', 'tenidas', 'tened',

'mas', 'si', 'tambien', 'que', 'el', 'mio', 'mia', 'mios', 'mias', 'estas',
'estais', 'estan', 'este', 'estes',  'esteis', 'esten', 'estare', 'estaras',
'estara', 'estareis', 'estaran', 'estaria', 'estarias', 'estariamos',
'estariais', 'estarian', 'estabamos', 'estuvieramos', 'estuviesemos', 'habeis',
'hayais', 'habreis', 'habran', 'habria', 'habrias', 'habriamos', 'habriais',
'habrian', 'habia', 'habias', 'habiamos', 'habiais', 'habian', 'hubiesemos',
'seais', 'sere', 'seras', 'sera', 'sereis', 'seran', 'seria', 'serias',
'seriamos', 'seriais', 'serian', 'eramos', 'fueramos', 'fuesemos', 'teneis',
'tengais', 'tendre', 'tendras', 'tendreis', 'tendran', 'tendria', 'tendrias',
'tendriamos', 'tendriais', 'tendrian', 'tenia', 'tenias', 'teniamos', 'teniais',
'tenian', 'tuvieramos', 'tuviesemos'])



def preprocessTokenizeText(text: str):

	"""Permite llevar a cabo el preprocesamiento de un texto realizando las
	siguientes acciones:

	1. Eliminar emoticonos y cualquier carácter no incluı́do en ASCII.
	2. Pasar el texto a minúscula.
	3. Eliminar sı́mbolos de puntuación y números del texto.
	4. Eliminar caracteres iguales y contiguos repetidos más de 2 veces y
		reemplazarlos por un sólo carácter
	5. Eliminar palabras de parada de full_sp_stopwords
	6. Eliminar palabras que sólo estén constituídas por una letra
	7. Eliminar algunas de la onomatopeyas usadas conmumente en el lenguaje
	8. Realizar stemming de las palabras con el algoritmo de Snowball de nltk
		antes citada

	Parámetros:
	-----------
	text: str
		Texto a preprocesar

	Devuelve:
	---------
		list de str. Lista de textos preprocesados
	"""

	#	Pasar texto a minúscula
	text = text.lower()

	#	Eliminar emoticonos
	text = text.encode('ascii','ignore').decode('utf-8')

	#	Eliminar símbolos de punctuación y números
	text = text.translate(text.maketrans('','',
										string.punctuation+'¿'+string.digits))

	#	Eliminar letras repetidas más de 2 veces
	text = re.sub(r'([a-z])\1{2,}', r'\1', text)

	#	Sustituir saltos de línea y tabuladores por espacios
	#text = text.translate(text.maketrans('\n\t','  ')) YA LO HACE SPLIT

	#	Separar las palabras
	text = text.split()

	#	Eliminar palabras de parada, expresiones y onomatopeyas
	for t in text:
		if (len(t)==1 or t in full_sp_stopwords or
							re.match('^(wow|uoh?|bua+h|xd|oh|[jakhs]+)$', t)):
			text.remove(t)

	#	Realizar stemming
	for i in range(len(text)):
		text[i] = __stemmer.stem(text[i])

	return text

def processRequest(text: str):

	"""Permite preprocesar un texto que contiene una pregunta para obtener
		el resumen de pregunta y el tipo (categoría semántica)

	Parámetros:
	-----------
	text: str
		Texto con la pregunta a procesar

	Devuelve:
	---------
		str o list de str. Lista de categorías semánticas asociadas a la
		pregunta: La primera categoría de la lista es la categoría semántica
		principal y el resto son categorías auxiliares.
	"""

	#   Eliminar los interrogantes del principio,
	#	pensar en si conviene quitar ? que estén en medio del texto
	text = re.sub(r'(^[¿¡]+([^ ])|([^ ])[\?!\.;,]+$)', r'\2\3', text)

	#   1. Pasar el texto a minúscula
	text = text.lower()

	#	2. Eliminar tildes
	text = text.translate(text.maketrans('áéíóú', 'aeiou'))

	#	3. Eliminar emoticonos
	#text = text.encode('ascii','ignore').decode('utf-8')

	#	Resumen pregunta y categoría semántica
	res, cat = None, None

	#   4. Tratar de emparejarlo con alguna expresión

	######################################################
	#   Expresión: ¿Qué es lo que hay que hacer para PV?
	#			  ¿Qué es lo que se hace para PV?
	#   Tipo: procedimiento
	######################################################
	m = re.search('que( es lo que)?( hay que hacer| se hac(?:e|ia)| hac(?:e|ia))(?: para)? (.+)', text)

	if m:
		res, cat = m.group(3), ['procedimiento', 'deber']

	############################
	#   Expresión: ¿Por qué no PV?
	#			  ¿Por qué no se PV?
	#			  ¿Por qué no hay que PV?
	#   Tipo: causa-negativa
	############################
	if not res:
		m = re.search('(?:por que|cual es la causa de(?: que)?) no(?: se)?(?: hac(?:iera|e)(?: par)?| hag(?:a|amos)(?: para)?| haya que| deb(?:e|eria|iera|emos|eriamos|ieramos)(?: de)?| pueda| pud(?:iera|ieramos)| pod(?:emos|iamos|amos|ido)| podr(?:ia|e|iamos|emos)|(?: me)? dej(?:e|ara)| me permit(?:a|iera)|(?: me)? haya dejado|(?: me)? haya permitido)? (.+)', text)

		if m:
			res, cat = m.group(1), 'causa-negativa'

	############################
	#   Expresión: ¿Por qué PV?
	#			  ¿Por qué se PV?
	#			  ¿Por qué hay que PV?
	#   Tipo: causa
	############################
	if not res:
		m = re.search('(?:por que|cual es la causa de(?: que)?)(?: se)?(?: hace(?: para)?| haga(?: para)?| hay que| hubiera(?:mos)? (?:que|de)| deb(?:a|amos|o|emos)(?: de)?| puedo| pod(?:emos|amos)| podr(?:ia|iamos)| pudamos|(?: me)? dej(?:e|ara)|(?: me)? permit(?:e|a)|(?: me)? permita| teng(?:a|o) que| tuvi(?:era|eramos) que)? (.+)', text)

		if m:
			res, cat = m.group(1), 'causa'

	############################
	#   Expresión: ¿Para qué sirve PN?
	#			  ¿ Para qué necesito PN?
	#			  ¿ Para qué uso PN?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('para que(?: sirven?| necesit(?:o|an|a|amos)| uso| usamos| usar(?:emos|iamos)| se usa(?:ria|ra|ba)| se uso) (.+)', text)

		if m:
			res, cat = m.group(1), ['finalidad', 'procedimiento', 'concepto']

	############################
	#   Expresión: ¿Qué es PN?
	#				¿Qué son PN?
	#				¿Quién es PN?
	#				¿Quienes son PN?
	#				¿Qué hace PN?
	#				¿Qué hacía PN?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('(?:que|quien(?:es)?) (es|son|seran?|eran?|hac(?:e|ia)?|hara) (.+)', text)

		if m:
			res, cat = m.group(2), ['concepto', 'finalidad', 'procedimiento',
									'posibilidad', 'momento', 'lugar', 'causa',
									'causa-negativa', 'finalidad', 'deber']

	############################
	#   Expresión: ¿Qué PN es PV?
	#				¿Qué PN son PV?
	#				¿Qué PN eran PV?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('(?:que|quien(?:es)) (.+) (es|son|seran?|eran?) (.+)', text)

		if m:
			res, cat = m.group(1)+' '+m.group(3), ['concepto', 'finalidad',
									'procedimiento', 'posibilidad', 'momento',
									 'lugar', 'causa', 'causa-negativa',
									 'finalidad', 'deber']

	############################
	#   Expresión: ¿Qué PN?
	#				¿Quién PN?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('(?:que|quien(?:es)) (.+)', text)

		if m:
			res, cat = m.group(1), ['concepto', 'finalidad', 'procedimiento',
									'posibilidad', 'momento', 'lugar', 'causa',
									'causa-negativa', 'finalidad', 'deber']

	#################################
	#   Expresiones:· ¿Cómo PV?
	#			   · ¿Cómo se PV?
	#			   · ¿Cómo hago para PV?
	#			   · ¿Cómo se hace para PV?
	#			   · ¿Cómo hay que PV?
	#   Tipo: procedimiento
	#################################
	if not res:
		m = re.search(
		'como( se)?( hac(?:e|ia)( para)?| hago( para)?| hay que| deb(?:o|eria|iera|emos|eremos)( de)?| puedo| podr(?:ia|e|iamos|emos))? (.+)',
																		text)

		if m:
			res, cat = m.group(6), ['procedimiento', 'deber', 'concepto']


	############################
	#   Expresión: ¿Cuál es la utilidad de PV?
	#			  ¿Cuál es el propósito de PV?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('cual(?:es)? (?:es|son) (?:el|la|los|las) (utilidad(?:es)|propositos?|finalidad(?:es)?|objetivos?) de (.+)', text)

		if m:
			#   El concepto se reordena y agrupa para hacerlo de la forma:
			#	¿Cuál es PN?
			res, cat = m.group(2), ['finalidad', 'concepto']

	############################
	#   Expresión: ¿Cuál es PN?
	#			  ¿Cuáles son PN?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('cual(?:es) (?:es|son) (.+)', text)

		if m:
			res, cat = m.group(1), ['concepto', 'procedimiento', 'posibilidad',
									'momento', 'lugar', 'causa',
									'causa-negativa', 'finalidad', 'deber']

	############################
	#   Expresión: ¿Cuál PN es el que PV?
	#			  ¿Cuáles PN son los que PV?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('cual(?:es) (.+) (es|son) (el|la|lo|las) que (.+)', text)

		if m:
			#   El concepto se reordena y agrupa para hacerlo
			#	de la forma: ¿Cuál es PN?
			res, cat = m.group(1)+' que '+m.group(4), ['concepto',
										'procedimiento', 'posibilidad','momento',
										'lugar', 'causa', 'causa-negativa',
										'finalidad', 'deber']

	############################
	#   Expresión: ¿Cuál PV?
	#			  ¿Cuáles PV?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('cual(?:es) (.+)', text)

		if m:
			#   El concepto se reordena y agrupa para hacerlo de la forma: ¿Cuál es PN?
			res, cat = m.group(1), ['concepto', 'procedimiento', 'posibilidad',
										'momento', 'lugar', 'causa',
										'causa-negativa', 'finalidad', 'deber']

	#################################
	#   Expresiones:· ¿Es necesario PV?
	#			   · ¿Es imprescindible que PV?
	#   Tipo: procedimiento
	#################################
	if not res:
		m = re.search('es (?:necesario|imprescindible|obligatorio|requerido)(?: que)? (.+)', text)

		if m:
			res, cat = m.group(1), ['deber', 'posibilidad', 'procedimiento']

	######################################################
	#   Expresión: ¿PN es PN?
	#	Tipo: concepto
	######################################################
	if not res:
		m = re.search('(.+) (es|son|seran?|eran?) (.+)', text)

		if m:
			res, cat = m.group(1)+' '+m.group(3), ['concepto', 'finalidad',
									'procedimiento', 'posibilidad', 'momento',
									'lugar', 'causa', 'causa-negativa',
									'finalidad', 'deber']

	############################
	#   Expresión: ¿Es posible PV?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('(?:es|son|eran?|seran?) posibles? (.+)', text)

		if m:
			res, cat = m.group(1), ['posibilidad', 'concepto', 'deber',
									'procedimiento']

	#################################
	#   Expresiones:· ¿Es PN ?
	#			   · ¿Son PN ?
	#   Tipo: procedimiento
	#################################
	if not res:
		m = re.search('(?:es|son) (.+)', text)

		if m:
			res, cat = m.group(1), ['concepto', 'procedimiento', 'posibilidad',
									'momento', 'lugar', 'causa',
									'causa-negativa', 'finalidad', 'deber']

	############################
	#   Expresión: ¿Cuándo se PV?
	#			  ¿Cuándo hay que PV?
	#   Tipo: momento
	############################
	if not res:
		m = re.search('(cuando|en que momento|en que circunstancias?)( se)?( hac(?:e|emos|ia)( para)?| hago( para)?| hay que| deb(?:e|eria|iera|emos|eriamos|ieramos)( de)?| pued(?:o|es?)| podr(?:ia|e|iamos|emos))? (.+)', text)

		if m:
			res, cat = m.group(7), ['momento', 'procedimiento', 'deber']

	############################
	#   Expresión: ¿Dónde se PV?
	#			  ¿Dónde hay que PV?
	#   Tipo: lugar
	############################
	if not res:
		m = re.search('(donde|en que( lugar)?)( se)?( hac(?:e|emos|ia)( para)?| hago( para)?| hay que| deb(?:e|eria|iera|emos|eriamos|ieramos)( de)?| pued(?:o|es?)| podr(?:ia|e|iamos|emos))? (.+)', text)

		if m:
			res, cat = m.group(8), ['lugar', 'procedimiento']

	############################
	#   Expresión: no puedo PV por qué
	#			  No me deja PV cuál es la causa
	#   Tipo: causa-negativa
	############################
	if not res:
		m = re.search('no (?:puedo|pod(?:emos|amos)|podr(?:ia|iamos)|pudamos|(?:me )?dej(?:e|ara|a)|(?:me )?permit(?:e|a)) (.+)(?: por que.*| cual es la caus.*)?', text)

		if m:
			res, cat = m.group(1), ['causa-negativa', 'causa', 'procedimiento']

	#################################
	#   Expresiones:· ¿Puedo PV?
	#			   · ¿Podría PV?
	#			   · ¿Se puede PV?
	#   Tipo: procedimiento
	#################################
	if not res:
		m = re.search('(se )?(puede|podr(?:ia|e|iamos|emos)|podemos) (.+)', text)

		if m:
			res, cat = m.group(3), ['posibilidad', 'procedimiento']

	#################################
	#   Expresiones:¿Se deberia PV?
	#			   · ¿Se debería de PV?
	#			   · ¿Se debe PV?
	#   Tipo: procedimiento
	#################################
	if not res:
		m = re.search('se deb(?:e|erian?|iera)(?: de)? (.+)', text)

		if m:
			res, cat = m.group(1), ['deber', 'posibilidad', 'procedimiento']

	#################################
	#   Expresiones:¿Debo de PV?
	#			   · ¿Debería PV?
	#			   · ¿Debiera de PV?
	#			   · ¿Debemos de PV?
	#   Tipo: procedimiento
	#################################
	if not res:
		m = re.search('deb(?:e|eria|iera|emos|eriamos|ieramos)(?: de)? (.+)',
																		text)

		if m:
			res, cat = m.group(1), ['deber', 'posibilidad', 'procedimiento']

	############################
	#   Expresión: ¿Puedo PV?
	#			  ¿Podría PV?
	#   Tipo: concepto
	############################
	if not res:
		m = re.search('(?:puedo| pod(?:emos|amos)| podr(?:ia|iamos)) (.+)', text)

		if m:
			res, cat = m.group(1), ['posibilidad', 'procedimiento', 'deber']

	############################
	#   Expresión: Quiero PV
	#   Tipo: procedimiento
	############################
	if not res:
		m = re.search('(?:Quiero|Querri(?:an?|mos)|Queremos) (.+) (?:como( se)?( hac(?:iera|e)( par)?| hag(?:a|amos)| hay que hacer(?:lo|la)?| deb(?:o|emos|ieramos|eriamos|amos)( de)? hacer(?:lo)| pued(?:o|es) hacer(?:lo)| pod(?:emos|iamos) hacer(?:lo)| podr(?:ia|iamos|emos) hacer(?:lo)) .*)?', text)

		if m:
			res, cat = m.group(1), ['procedimiento', 'concepto', 'posibilidad']

	#   Si no empareja con ninguna, se asume que el texto introducido es el
	#   concepto solicitado
	if not res:
		res, cat = text, None

	#   5. Tokenizar el texto resultante
	res = res.split()

	#   6. Eliminar palabras de parada
	i = 0
	while i < len(res):
		if res[i] in red_sp_stopwords:
			del res[i]
		else:
			i += 1

	#   7. Aplicar el stemming
	for w in range(len(res)):
		res[w] = __stemmer.stem(res[w])

	res = ' '.join(res)

	#	Devolver resumen pregunta y categoría semántica
	return res, cat

def compare_words(a: str, b: str):

	"""
	Función que calcula la diferencia semántica entre dos palabras. La
	comparación se realiza atendiendo a la siguiente regla:

	- Si palabras(a) incluída en palabras(b) o
		palabras(b) incluída en palabras(a)
		-> Devuelve el número de palabras que son diferentes

	- En caso contrario se devuelve un valor nulo

	Parámetros
	----------
	a : str
	 	Primera cadena a comparar

	b : str
	 	Segunda cadena a comparar

	Devuelve
	--------
	int o None: El número de palabras que son diferentes si una cadena está
	 	incluída en otra o None si ninguna cadena está incluída en la otra

	"""

	#	Alguna de las dos cadenas está avcía y se devuelve infinito
	if not a or not b:
		return None

	#	Considerar la cadena de mayor tamaño y la de menor tamaño
	mayor = a if len(a) >= len(b) else b
	menor = b if len(a) >= len(b) else a

	d = 0 #	Número de palabras diferentes en ambas cadenas

	#	Separar palabras
	mayor = mayor.split()
	menor = menor.split()


	#	Se comparan las palabras de cada cadena
	i = 0
	j = 0

	while i < len(mayor) and j < len(menor):

		if mayor[i] == menor[j]:
			j+=1	#	Coinciden las palabras
		else:
			d+=1	#	Se contea una palabra diferente

		i+=1

	#	Si se sale del bucle antes de terminar la comparación por haber
	#	encontrado que la cadena menor está incluída en la mayor, añadir
	#	automáticamente el resto de palabras de la mayor a d
	if i < len(mayor):
		d += len(mayor) - i

	if j == len(menor):
		#	La cadena menor está incluída en la mayor
		return d
	else:
		#	La cadena menor no está incluída en la mayor
		return None

def parseSpeechDate(date: str):

	"""Toma una fecha formulada en lenguaje natural y obtiene la fecha
		correspondiente

	Parámetros:
	-----------
		date: str
		Fecha formulada en lenguaje natural

	Devuelve:
	---------
		datetime.datetime o None. Fecha correspondiente a la expresada en el texto
		pasado como argumento. Se devuelve None si no se reconoce la fecha
	"""

	ret_date = datetime.datetime.now()

	#Meses y días de la semana es español
	meses = {
				'enero': 1,
				'febrero':2,
				'marzo': 3,
				'abril': 4,
				'mayo': 5,
				'junio': 6,
				'julio' : 7,
				'agosto' : 8,
				'septiembre': 9,
				'octubre': 10,
				'noviembre': 11,
				'diciembre': 12
		}

	dias_semana = {
					'lunes': 1,
					'martes': 2,
					'miércoles': 3,
					'miercoles': 3,
					'jueves': 4,
					'viernes': 5,
					'sábado': 6,
					'sabado': 6,
					'domingo': 7
			}

	offset_dia = {
					'hoy': 0,
					'mañana': 1,
					'pasado mañana': 2,
					'ayer': -1,
					'anteayer': -2,
					'ahora': 0,
					'mediodia': 0,
					'medianoche': 1,
					'tarde': 0
			}

	#Formado dd/mm/aaaa
	m = re.search('([0-9]{1,2})[-/]([0-9]{1,2})[-/]([0-9]{4})', date)

	if m:

		try:
			ret_date = ret_date.replace(day=int(m.group(1)),
										month=int(m.group(2)),
										year=int(m.group(3)))

			return ret_date

		except:
			return None

	#Formado aaaa/mm/dd
	m = re.search('([0-9]{4})[-/]([0-9]{1,2})[-/]([0-9]{1,2})', date)

	if m:
		try:
			ret_date = ret_date.replace(day=int(m.group(3)),
										month=int(m.group(2)),
										year=int(m.group(1)))

			return ret_date

		except:
			return None

	#Formato (día) de (mes) de (año)
	m = re.search(('([0-9]{1,2}) de (%s)( de ([0-9]{4}|este año))?' %
										'|'.join(meses.keys())), date.lower())

	if m:
		try:
			ret_date = ret_date.replace(day=int(m.group(1)),
														month=meses[m.group(2)])

			if m.group(4) is not None and m.group(4)!='este año':
				ret_date = ret_date.replace(year=int(m.group(4)))

			return ret_date

		except:
			return None

	#Formato el (dia de la semana)
	m = re.search(('(?:el|este|el pr[óo]ximo|el siguiente)? (%s)' %
								'|'.join(dias_semana.keys())) , date.lower())

	if m:
		cur_weekday = ret_date.weekday()
		new_weekday = (dias_semana[m.group(1)]-1) - cur_weekday

		#	Día de la próxima semana
		if new_weekday<0:
			new_weekday += 7
		elif new_weekday == 0:
			new_weekday = 7

		ret_date = ret_date.replace(day=ret_date.day+new_weekday)

		return ret_date

	#Formato (hoy, mañana, pasado, etc)
	m = re.search('(%s)' % '|'.join(offset_dia.keys()) , date.lower())

	if m:

		#	Tomar el offset y sumarlo
		offset = offset_dia[m.group(1)]

		ret_date += datetime.timedelta(days=offset)
		return ret_date

	#	Formato (dentro de 2 semanas)
	m = re.search('(dentro de|en|pasados?)? ([0-9]+) d[ií]as?' , date.lower())

	if m:

		#	Tomar el incremento de semanas
		offset = int(m.group(2))

		ret_date += datetime.timedelta(days=offset)
		return ret_date

	#	Formato (dentro de 2 semanas)
	m = re.search('(dentro de|en|pasados?)? ([0-9]+) semanas?' , date.lower())

	if m:

		#	Tomar el incremento de semanas
		offset = int(m.group(2))

		ret_date += datetime.timedelta(weeks=offset)
		return ret_date

	return None

def parseSpeechTime(time: str):

	"""Toma una hora formulada en lenguaje natural y obtiene la hora y minutos
		correspondientes

	Parámetros:
	-----------
	time: str
		Hora formulada en lenguaje natural

	Devuelve:
	---------
		list de int o None. Lista con dos enteros que se hacen corresponder
			con la hora y minutos respectivamente. Se devuelve None si no
			se reconoce la hora expresada
	"""

	offset_minute = {
					'en punto': 0,
					'y pico': 10,
					'y cuarto': 15,
					'y media': 30,
					'menos cuarto': -15
				}

	time_speech = {
						'ahora': [datetime.datetime.now().hour,
										datetime.datetime.now().minute],
						'mediodia': [12,0] ,
						'medianoche': [0,0],
						'madrugada': [0,0],
						'tarde': [17,0]
				}

	interval_hour = {
					'de la mañana': (0, 12),
					'de la tarde':  (12, 0),
					'de la noche':  (18, 6),
					'de la madrugada': (0, 12),
					'del mediodia': (12, 15)
				}

	ret_time = [0,0]

	#	Formato (a las 6 de la mañana)
	m = re.search(('([0-9]{1,2}) (%s)' %
								'|'.join(interval_hour.keys())), time.lower())

	if m:

		ret_time[0] = int(m.group(1))

		interval = interval_hour[m.group(2)]

		#	Se invalidan las horas mayores de 12
		if ret_time[0] > 12:
			return None

		ret_time[0] %= 12 #	Reducir la hora al intervalo [0-12)

		#	Obtener la hora en el formato 24 horas a partir de la información
		#	del intervalo

		if ret_time[0] >= (interval[0] % 12):
			ret_time[0] = (interval[0]//12)*12 + ret_time[0]

		elif ret_time[0] <= (interval[1] % 12):
			ret_time[0] = (interval[1]//12)*12 + ret_time[0]

		else:
			return None

		return ret_time

	#	Formato (a las 6 de la mañana)
	m = re.search(('(.+) (%s)' %
								'|'.join(interval_hour.keys())), time.lower())

	if m:

		ret_time[0] = parseSpeechTime(m.group(1))

		interval = interval_hour[m.group(2)]

		#	Se invalidan las horas mayores de 12
		if ret_time[0] > 12:
			return None

		ret_time[0] %= 12 #	Reducir la hora al intervalo [0-12)

		#	Obtener la hora en el formato 24 horas a partir de la información
		#	del intervalo

		if ret_time[0] >= (interval[0] % 12):
			ret_time[0] = (interval[0]//12)*12 + ret_time[0]

		elif ret_time[0] <= (interval[1] % 12):
			ret_time[0] = (interval[1]//12)*12 + ret_time[0]

		else:
			return None

		return ret_time

	#Formato hh y expresion de minuto
	m = re.search(('([0-9]{1,2})( (%s))' % '|'.join(offset_minute.keys())),
																time.lower())

	if m:

		#if m.group(3) is not None:
		aux = int(m.group(1))*60
		aux += offset_minute[m.group(3)]
		#else:
		#	aux = int(m.group(1))

		ret_time[0] = aux//60
		ret_time[1] = aux%60

		return ret_time if ret_time[0] < 24 else None

	#	Usar alguna expresión de tiempo
	m = re.search('(%s)' % '|'.join(time_speech.keys()), time.lower())

	if m:
		return time_speech[m.group(1)]

	#	Formato (dentro de 2 horas)
	m = re.search('(dentro de|en) (([0-9]+) horas?( y )?)?(([0-9]+) minutos?)?',
					time.lower())

	if m:

		#	No se ha especificado ninguna hora ni minuto
		if not m.group(3) and not m.group(6):
			return None

		aux = datetime.datetime.now()
		ret_time = [aux.hour, aux.minute]

		#	Para determinar los incrementos
		offset_hour = offset_minutes = 0

		#	Tomar el incremento de minutos y de horas acumuladas
		if m.group(6) is not None:
			offset_minutes = int(m.group(6))
			ret_time[1] += (offset_minutes % 60)
			ret_time[0] += (offset_minutes // 60)

		#	Tomar el incremento de horas
		if m.group(3) is not None:
			offset_hour = int(m.group(3))
			ret_time[0] = (offset_hour % 24)

		return ret_time

	#Formato hh y mm
	m = re.search('([0-9]{1,2}) +y +([0-9]{1,2})', time)

	if m:

		ret_time[0] = int(m.group(1))
		ret_time[1] = int(m.group(2))

		return ret_time if ret_time[0] < 24 and ret_time[1] < 60 else None

	#Formato hh:mm
	m = re.search('([0-9]{1,2}):([0-9]{1,2})', time)

	if m:
		ret_time[0] = int(m.group(1))

		if m.group(2):
			ret_time[1] = int(m.group(2))

		return ret_time if ret_time[0] < 24 and ret_time[1] < 60 else None

	return None

def replaceSpeechNumber(speech: str):

	"""Toma un texto con números expresados en lenguaje natural y devuelve
		un texto similar al que se pasa como entrada donce los números
		han sido reemplazados por sus correspondientes valores numéricos

		Nota: Sólo es capaz de aplicar esta operación a los valores
		comprendidos en el intervalo [0,100)

	Parámetros:
	-----------
	speech: str
		Texto que incluye números expresados en lenguaje natural

	Devuelve:
	---------
		str Texto resultante
	"""

	unidades = ['cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis',
													'siete', 'ocho', 'nueve']
	especiales = ['once', 'doce', 'trece', 'catorce', 'quince']
	decenas = ['diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta',
									'sesenta', 'setenta', 'ochenta', 'noventa']
	decenas_pref = ['dieci', 'veinti']

	#	Texto con el número en minúscula
	speech = speech.lower()

	#	Texto sin tildes
	speech = speech.translate(speech.maketrans('áéíóú', 'aeiou'))

	num = 0 #	Número parseado

	while num is not None:
		#	Repetir hasta sustituir todas las expresiones por números
		num = None

		#####################################################
		#	Buscar número que tengan las decenas de 10 y 20 #
		#####################################################
		m = re.search('(%s)(%s)' % ('|'.join(decenas_pref),
											'|'.join(unidades[1:])),
											speech)

		if m:
			#	Determina el valor del número
			num = (decenas_pref.index(m.group(1))+1)*10 + unidades.index(
																	m.group(2))

			if num and num > 15:
				speech = speech.replace(m.group(0), str(num))
			continue

		######################################################################
		#	Buscar otros números que contengan decenas diferentes a 10 y 20  #
		######################################################################
		m = re.search('(%s)( +y +(%s))' % ('|'.join(decenas[2:]),
													'|'.join(unidades[1:])),
													speech)

		if m:

			num = 0 #	Establecer el valor a 0

			if m.group(3):
				#	Se determina la unidad que acompaña a la decena
				num += unidades.index(m.group(3))

			#	Añadir el valor de la decena
			num += (decenas.index(m.group(1))+1)*10

			#	Reemplazar la expresión por el valor del número
			speech = speech.replace(m.group(0), str(num))

			continue

		#######################################################
		#	Parsear con unidades, números especiales, 10 y 20 #
		#######################################################
		m = re.search('(%s)' % ('|'.join(unidades) +'|'+ '|'.join(especiales) +
												'|'+ '|'.join(decenas)),
																		speech)

		if m:

			if m.group(1) in unidades:
				num = unidades.index(m.group(1))

			elif m.group(1) in especiales:
				num = especiales.index(m.group(1)) + 11

			else:
				num = (decenas.index(m.group(1)) + 1)*10

			#	Reemplazar la expresión en la cadena speech por el
			#	valor del número
			speech = speech.replace(m.group(1), str(num))

			continue

	return speech
