import os
import time
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv
import numpy as np
from collections import Counter, defaultdict
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from scene_separator import Scene

scene_amount_per_query = 14
system_instructions_Spanish =[
                """
                Recibirás un guion con sus escenas y devolverás los personajes que aparecen físicamente en cada escena así como la continuidad entre escenas. Devuelve la respuesta en el formato: Escena número de escena- Continuidad [número de escena de la que viene, número de escena a la que va] personaje 1: razón por la que consideras que el personaje está en la escena~ personaje 2: razón por la que consideras que el personaje está en la escena
                Se dice que de las escena s se va la escena t si imaginando que la película fuera filmada con un plano consecutivo, es decir, con una misma cámara que se mueve hacia donde vayan los personajes incluso cuando se cambia de escena, la acción entre una escena y otra fuera consecutiva.
                Ejemplo 1:
                Escena 1: Continuidad [X,2] El personaje 1 está corriendo en el parque.
                Escena 2:  Continuidad [1,X] El personaje 2 saluda al personaje 1 desde su balcón.
                En este caso, la respuesta es:
                escena 1: personaje 1
                escena 2: personaje 2 (el personaje 1 no está presente en la escena 2 porque las escenas tuvieron lugar en diferentes escenarios).
                Ejemplo 2:
                Escena 1: El personaje 1 está gritando a alguien desde su casa.
                Escena 2: El personaje 2 está en un lugar diferente a la casa del personaje 1 pero escucha los gritos y saluda al personaje 1.
                En este caso, la respuesta es:
                escena 1:  Continuidad [X,2] personaje 1
                escena 2:  Continuidad [1,X] personaje 2 (en la escena 2 no se menciona que el personaje 1 reaccione a algo)
                Ejemplo 3:
                Escena 1: El personaje 1 está gritando a alguien desde su casa.
                Escena 2: El personaje 2 está en un lugar diferente a la casa del personaje 1 pero escucha los gritos y responde: ¡Buenos días, señor!.
                En este caso, la respuesta es:
                escena 1: Continuidad [X,2] personaje 1
                escena 2: Continuidad [1,X] personaje 2 (en la escena 2 no se menciona que el personaje 1 reaccione a algo y en la escena anterior ya vimos la acción que hizo el personaje 1 para causar una reacción en el personaje 2, por lo tanto, no es necesario mostrar al personaje 1 en esta escena)
                Ejemplo 4:
                Escena 1: El personaje 1 está gritando a alguien desde su casa.
                Escena 2: El personaje 2 está en un lugar diferente a la casa del personaje 1 pero escucha los gritos y saluda al personaje 1. El personaje 1 lo mira.
                En este caso, la respuesta es:
                escena 1: Continuidad [X,2] personaje 1
                escena 2: Continuidad [1,X] personaje 2, personaje 1 (en la escena 2 el personaje 1 realiza la acción de mirar)
                Ejemplo 5:
                Escena 1: El personaje 1 está gritando a alguien desde su casa.
                Escena 2: El personaje 2 está en un lugar diferente a la casa del personaje 1 pero escucha los gritos y saluda al personaje 1, diciendo: Hola, amigo.
                En este caso, la respuesta es:
                escena 1: Continuidad [X,2] personaje 1
                escena 2: Continuidad [1,X] personaje 2 (en la escena 2 no se menciona que el personaje 1 reaccione a algo)
                Ejemplo 6:
                Escena 1: El personaje 1 está gritando a alguien desde su casa.
                Escena 2: El personaje 2 está en un lugar diferente a la casa del personaje 1 pero cree ver al personaje 1 saludando y saluda al personaje 1, diciendo: Hola, amigo.
                En este caso, la respuesta es:
                escena 1: Continuidad [X,2] personaje 1
                escena 2: Continuidad [1,X]personaje 2 (en la escena 2 no se menciona que el personaje 1 reaccione a algo, el personaje 2 reacciona a la acción de personaje 1 en la escena anterior)
                Ejemplo 7:
                Escena 1: El personaje 1 está gritando a alguien desde su casa.
                Escena 2: El personaje 2 está en un lugar diferente a la casa del personaje 1 pero cree ver al personaje 1 saludando y devuelve el saludo al personaje 1, diciendo: Hola, amigo.
                En este caso, la respuesta es:
                escena 1: Continuidad [X,2] personaje 1
                escena 2: Continuidad [1,X] personaje 2 (en la escena 2 no se menciona que el personaje 1 reaccione a algo, el personaje 2 reacciona a la acción de personaje 1 en la escena anterior porque cree verlo, pero ya se mostró al personaje 1 en la escena anterior. es decir, lo que personaje 2 cree es un elemento visual que se mostró en escena 1, luego no aparece en escena 2, por lo tanto personaje 1 no aparece)
                Ejemplo 8:
                Escena 1: El personaje 1 lanza una pelota desde su cuarto y cae por la ventana.
                Escena 2: El personaje 2 está en su patio, le cae la pelota delante y la lanza por la ventana para devolverla al personaje 1, gritándole: Ahí te va!
                En este caso, la respuesta es:
                escena 1: Continuidad [X,2] personaje 1
                escena 2: Continuidad [1,X] personaje 2 (en la escena 2 no se menciona que el personaje 1 reaccione a algo, el personaje 2 reacciona a la acción de personaje 1 al encontrar su pelota y la lanza, pero no se ve al personaje 1 recibiéndola ni observando la acción)
                Ejemplo 9:
                Escena 1: El personaje 1 mueve sus brazos.
                Escena 2: El personaje 2 está en su patio, cree que lo saludan y devuelve el saludo a personaje 1.
                En este caso, la respuesta es:
                escena 1: Continuidad [X,X] personaje 1
                escena 2: Continuidad [X,X] personaje 2 (en la escena 2 no se menciona que el personaje 1 reaccione a algo, el personaje 2 cree ver al personaje 1 saludando y por eso hace la acción de saludar. En la escena no hay mención de cómo reacciona el personaje 1 y el saludo no requiere la presencia de ambas personas)
                Ejemplo 10:
                Escena 1: El personaje 1 está en su cuarto y su abuela entra y le pide que salga al patio.
                Escena 2: El personaje 1 se ve entrando al patio.
                En este caso, la respuesta es:
                escena 1: Continuidad [X,2] personaje 1, abuela (La escena 2 debe ocurrir a continuación de la 1 porque el personaje 1 se dirigió de su cuarto al patio)
                escena 2: Continuidad [1,X] personaje 2 (la escena viene de la escena 1 porque sabemos que la acción de llegar al patio ocurre directamente después de que al personaje 1 se le pide salir de su cuarto, debido a que en la escena anterior me implican que el muchacho saldrá del cuarto)
                Ejemplo 11:
                Escena 1: El personaje 1 está triste en la mesa del comedor pensando en su novia.
                Escena 2: La novia del personaje 1 está en el patio de su casa y busca a su hermana menor.
                Escena 3: El personaje 1 se levanta de la mesa del comedor y va hacia su cuarto.
                Escena 4: El personaje 1 sale al día siguiente de su casa.
                En este caso, la respuesta es:
                escena 1: Continuidad [X,3] personaje 1 (en la escena 3 se continúa la historia del muchacho en el mismo lugar en el que se dejó en escena 1)
                escena 2: Continuidad [X,X] novia
                escena 3: Continuidad [1,X] personaje 1
                escena 4: Continuidad [X,X] personaje 1 (no continúa la acción de escena 3 porque ocurre al día siguiente, luego pasa mucho tiempo entre que el muchacho entra a su cuarto y los eventos de la escena 4)
                """
            ]

system_instructions_English =[
                """
                You will receive a script with its scenes and return the characters that physically appear in it per scene in the format: Scene number- character1, character2,etc.
                A character only appears in a scene if its actor is going to appear in a shot from the scene, meaning that the actor's body or face should appear on the screen or the scene is not possible.
                Example 1:
                Scene 1: Character 1 is running in the park.
                Scene 2: Character 2 waves at Character 1 from their balcony.
                In this case, Character 1 is not present in Scene 2 because the scenes took place in different settings.
                Example 2:
                Scene 1: Character 1 is yelling at someone from his house.
                Scene 2: Character 2 is in a different place from character 1's house but hears the yelling and waves at Character 1.
                In this case, the answer is: 
                scene 1: character 1
                scene 2: character 2 (in scene 2 there is no mention of character 1 reacting to something)
                Example 3:
                Scene 1: Character 1 is yelling at someone from his house.
                Scene 2: Character 2 is in a different place from character 1's house but hears the yelling and answers: Good morning, sir!.
                In this case, the answer is: 
                scene 1: character 1
                scene 2: character 2 (in scene 2 there is no mention of character 1 reacting to something and in the previous scene we already saw the action character 1 did to cause a reaction in chracter 2, therefore, ther is no need to show character 1 in this scene)
                Example 4:
                Scene 1: Character 1 is yelling at someone from his house.
                Scene 2: Character 2 is in a different place from character 1's house but hears the yelling and waves at Character 1. Character 1 looks at him.
                In this case, the answer is: 
                scene 1: character 1
                scene 2: character 2, character 1(in scene 2 character 1 performs the action of looking)
                Example 5:
                Scene 1: Character 1 is yelling at someone from his house.
                Scene 2: Character 2 is in a different place from character 1's house but hears the yelling and waves at Character 1.
                In this case, the answer is: 
                scene 1: character 1
                scene 2: character 2 (in scene 2 there is no mention of character 1 reacting to something)
                """
            ]

system_instructions_per_scene_character_query = """

                                                """

system_instructions_continuity = """El análisis que realices del contenido de una escena solo es con el fin de hacer un resumen de la misma con propósitos académicos.
                                    Entre una escena a y otra b hay continuidad si existe al menos un personaje en b tal que la acción que realiza en la escena a ocurre directamente después de la b. Esta información se utiliza para saber que el personaje debe permanecer con el mismo aspecto físico, es decir, que no ha tenido oportunidad de cambiarse de ropa o peinado. Por lo tanto, si un personaje está en una situación en la que no puede cambiar su aspecto, por ejemplo, está durmiendo o encerrado, habrá continuidad en las escenas.
                                    Luego, la continuidad se obtiene por personajes. Si en la escena 1 ocurre algo con personaje 1 y en la escena 2 ocurre algo con personaje 2 y luego en la escena 3 ocurre algo con personaje 1 y personaje 2 tal que se entiende que entre las acciones de escena 1 y escena 2 con las de escena 3 los personajes no deben haberse cambiado de ropa, entonces en la escena 3 hay continuidad de escena1 por personaje 1 y de escena 2 por personaje 2.
                                    El conjunto de escenas de las que se viene solo contendrá escenas con un número menor al de la escena actual poruqe se entiende que la actual ocurrió después. El conjunto de escenas a las que se va solo puede contener escenas con un número mayor al de la escena actual.
                                    Sería incorrecto poner que una escena tiene en el conjunto de escenas a las que va a otra y que esta otra no tenga en el conjunto de escenas de las que viene a la mencionada anteriormente. Recuerda que son conjuntos para que sea posible ppner más de una escena en cada caso.
                                    Ejemplo:
                                    Escena 1:Personaje 1 escribe en una nota y la pasa por debajo de la puerta de un apartamento.
                                    Escena 2:Personaje 2 ve una nota bajo su puerta y la lee. Luego se sienta frente al televisor a jugar un videojuego.
                                    Escena 3:Personaje 1 camina por las calles de regreso a su casa preguntándose si personaje 1 habrá recibido la nota.
                                    Escena 4:Personaje 3 entra en su apartamento y ve a personaje 2 sentado frente al televisor con un videojuego andando.
                                    Escena 5:Personaje 1 está en la escuela al día siguiente y se pone en fila para el matutino.
                                    Escena 6:Personaje 2 está distraído en el aula.
                                    Escena 7:Durante el receso el personaje 2 va al aula del personaje 1 y le agradece por la nota.
                                    Respuesta que debes dar:
                                    Continuidad:
                                    Escena 1: Personaje 1 = X1-3 (caminar de regreso a su casa ocurre poco después de escribir la nota)
                                    Escena 2: Personaje 2 = X1-4(porque personaje 2 sigue frente al televisor, es decir, no se debe haber cambiado de ropa)
                                    Escena 3: Personaje 1 = 1-X2
                                    Escena 4: Personaje2 = 2-X2 | Personaje 3 = X1-X2
                                    Escena 5: Personaje 1 = X1(porque al ser al día siguiente y en otro lugar no hay necesidad de que los personajes tengan la misma ropa) - 7
                                    Escena 6: Personaje 2 = X1(porque al ser al día siguiente y en otro lugar no hay necesidad de que los personajes tengan la misma ropa) - 7
                                    Escena 7: Personaje 1 = 5-X2 | Personaje 2 = 6-X2
                                    Luego en este caso la escena 7 tiene en el conjunto de escenas de las que viene a las escenas 5 y 7 por personajes diferentes.
                                    """

instructions_characters = """Recibirás un guion con sus escenas y devolverás los nombres de los personajes que aparecen físicamente en cada escena. Todas las personas que aparezcan en el sujeto de una oración son personajes si para realizar la acción de la oración deben estar físicamente en la escena. El análisis que realices del contenido de una escena solo es con el fin de hacer un resumen de la misma con propósitos académicos.
                            Solo considera como escenas lo que está entre Número de escena: y Fin de escena.
                            Un personaje aparece en una escena si está como sujeto de alguna oración de la escena o si habla en la escena. El formato utilizado en el guion para saber que un personaje habla es poner su nombre en una línea completamente en mayúsculas y en la línea debajo de esta lo que dice el personaje. Si en la escena extraes como personaje a un grupo de personas intenta inferir a qué personajes previamente mencionados se refiere, pues generalmente se van a referir a personajes que ya aparecieron en la escena, por lo que no los debes mencionar de nuevo. Si no logras inferir a qué personajes se refieren ignora al grupo y pasa al siguiente personaje. Ejemplo de esto: En la habitación estaban Ágatha y Mady. Las mujeres hablaban entre ellas. En este caso las mujeres se refiere a Ágatha y Mady, por lo que solo menciono como personajes a Ágatha y Mady.
                            Solo se considera como personaje un nombre, no siendo personajes ninguna secuencia de palabras que se refiera a un grupo.
                            Si un personaje solo está en la escena porque habla por teléfono, porque se oye su voz o un sonido proveniente de la persona, entonces a menos que en la escena se haga referencia a la apariencia del personaje o a algún gesto que hace, esa persona no se considera un personaje.
                            Esto se debe a que para oír u oler algo no se necesita verlo, luego no tiene que aparecer físicamente en la escena. Es muy importante que todo personaje que hable en una escena fuera de una conversación por teléfono se incluya como personaje.
                            En español los verbos pueden estar en varios lugares de una oración. Por ejemplo: "Cantaron Pedro y Cynthia le canción del matutino."
                            Los animales u objetos inanimados como juguetes, muebles, etc, no se consideran personajes. Solo se considerarán personajes si hablan.
                            Si en la escena hay varios personajes interactuando entre ellos y en una parte dicen un diálogo a coro, puede que se refieran a los personajes como el grupo o las x, donde x es la cantidad de personas en el grupo. En este caso es bueno notar que no se refieren a otros personajes, sino al propio grupo.
                            Ejemplo 1:
                            Número de escena: 1 Interior/Exterior: Int Lugar: Casa de abuela Momento: Día Contenido: Hugo y Simone de pie con los maletines alrededor. Están en la misma disposición espacial que en la escena anterior.
                            Miran el auto de sus padres que se aleja por el terraplén. Detrás de ellos, la casa de la abuela.
                            Por el entorno todo indica que es un pueblo de campo como Canasí o Jaruco.
                            EVA (70), la abuela de los niños, los observa parada desde el portal de la casa. La señora es de rostro duro. Viste de manera sobria y tradicional.
                            Eva pronuncia el nombre de su nieta tal cual se escribe: «Simone».
                            EVA
                            (grita como una generala)
                            ¡Simone, Hugo, entren ya!
                            Hugo habla sin voltearse.
                            HUGO
                            (para sí)
                            Y así comienza. Fin de escena
                            Respuesta que debes dar en este caso:
                            Escena 1: Hugo - de pie | Simone - de pie | Eva - observa
                            Nota: en el ejemplo 1 hablan Hugo y Eva.
                            Ejemplo 2:
                            Número de escena: 1 Interior/Exterior: Int Lugar: Galería Momento: Medianoche Contenido: Juan y Claudia están dándose la mano en la galería. Patricia mira los cuadros. Juan: Mira a Carla!Qué hermosa se ve! El cuadro en que aparece Carla está colgado al final de un pasillo. Fin de escena
                            La respuesta que me debes dar en este caso es:
                            Escena 1: Juan - está en la galería | Claudia - está en la galería | Patricia - mira los cuadros
                            Ejemplo 3:
                            Número de escena: 1 Interior/Exterior: Ext Lugar: Portal de Juana Momento: Medianoche Contenido: Juana, Lucía y Tabitha están sentadas en el portal.
                            JUANA
                            (pregunta al aire)
                            Y entonces qué hago?
                            TABITHA
                            (para sí) 
                            Ojalá supiera
                            Pasa un señor por la calle al que no vemos y las saluda.
                            SEÑOR
                            Hola, familia
                            LAS TRES
                            Hola
                            Fin de escena
                            La respuesta que me debes dar en este caso es:
                            Escena 1: Juana - está sentada | Tabitha - está sentada | Lucía - está sentada
                            Nota: El señor que saluda se dice explícitamente en la escena que no se ve, por lo que no se incluye como personaje. Cuando hablan las tres se refiere al grupo de las tres mujeres mencionadas antes porque en ninguna parte de la escena se menciona otro grupo como las tres, lyego deben ser Juana, Tabitha y Lucía. Por tanto las tres no se incluye como personaje nuevo.                           
                            Ejemplo 4:
                            Número de escena: 1 Interior/Exterior: Int Lugar: Galería Momento: Medianoche Contenido: Están Juan y Claudia dándose la mano en la galería. Patricia mira los cuadros. El sonido de Hugo tocando la trompeta los pone nerviosos. No lo esperaban en este momento. Los olores que provienen del plato que cocina Ramona los llaman a comer. Fin de escena
                            La respuesta que me debes dar en este caso es:
                            Escena 1: Juan - está en la galería | Claudia - está en la galería | Patricia - mira los cuadros
                            Nota: Hugo hace un sonido pero no se referencia su apariencia ni gestos, ni aparece un diálogo dicho por él, luego no se considera un personaje de esta escena. Pasa algo parecido con Ramona, que está cocinando en alguna parte porque se siente el olor de su platillo, pero no la vemos en la escena.
                            """

class Character(object):
    def __init__(self, count, context):
        self.count = count
        self.context = context                               

scenes = [Scene(1,"INT","Casa", "Día", (1,333), 1, {"Carlos": Character(1,"")}, "", "El vecino de los Addams, Carlos, grita descontroladamente." ), Scene(2,"INT","Casa", "Día", (1,333), 1, {"Gómez": Character(1,""), "Morticia": Character(1,"")}, "", "Gómez y Morticia miran atónitos a su vecino. Gómez cree ver al vecino sonriendo y le grita. Gómez: No me esperaba tanta intensidad de ti, viejo amigo."), Scene(3,"INT","Patio", "Día", (1,333), 1, {"Carlita": Character(1,""), "Tray": Character(1,"")}, "", "Carlita: Vamos Juan, no seas bobo. Dice Carlita dirigiéndose a su mono de peluche. Tray entra corriendo y eleva su puño al cielo con desdén."), Scene(4,"INT","Casa", "Día", (1,333), 1, {"Gómez": Character(1,"")}, "", "Gómez cree ver a Tray saludándolo y le devuelve el saludo diciendo: Buenos días. Gómez corre hacia la puerta que da al patio y sale."), Scene(5,"INT","Patio", "Día", (1,333), 1, {"Gómez": Character(1,""), "Tray": Character(1,"")}, "", "Gómez está sentado al lado de Tray y le pregunta cómo se siente." ), Scene(7,"INT","Casa", "Noche", (1,333), 2, {"Gómez": Character(1,"")}, "", "Gómez se pasea por la galería de su casa"), Scene(7,"EXT","Calle", "Día", (1,333), 2, {"Rodolfo": Character(1,"")}, "", "Se ve a un hombre joven (Rodolfo), que corre por la calle huyendo de unos autos de policía. Ve un almacén y entra para esconderse. Rodolfo prepara una especie de cama improvisada con una tela y se acuesta."), Scene(8,"INT","Comisaría", "Día", (1,333), 3, {"Montalbo": Character(1,"")}, "", "El comisario Montalbo habla al teléfono. Montalbo: Cómo que se escapó? Lo atraparé yo mismo. Cuelga el teléfono rápidamente" ), Scene(9,"INT","Gasolinera", "Día", (1,333), 3, {"Montalbo": Character(1,"")}, "", "El comisario Montalbo pregunta por la cinta de seguridad de la gasolinera. El comisario recibe una llamada a su móvil y responde: Gracias, revisaré ese lugar."), Scene(10,"INT","Almacén", "Día", (1,333), 4, {"Montalbo": Character(1,""), "Rodolfo": Character(1, "")}, "", "El comisario abre la puerta del almacén con sigilo. Revisa los rincones del lugar y ve la cama improvisada preparada por el sospechoso. Encuentra a Rodolfo tratando de escapar y lo apresa." ) ]



MAX_RETRIES = 5  # Maximum number of attempts for the Gemini API

class CharacterExtractor:
    def __init__(self, config_file='.env'):
        # Load environment variables from the .env file
        load_dotenv(config_file)

        # Configure Gemini AI API using the API key
        self.api_key = os.environ['GENAI_API_KEY']
        genai.configure(api_key=self.api_key)
        
    def start_new_chat(self, system_instruction):
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        self.chat = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    },
            system_instruction = system_instruction
        ).start_chat(history=[])


    def extract_characters(self, scenes, query_amount):
        script_characters = set()
        # Extract characters from the text using Gemini AI and return them
        # correct_answers_per_scene = [0 for _ in range(len(scenes))]
        # for scene in scenes:
        #     scene.characters = {}
        # t = 0
        # for i in range(10):
        #     for scene in scenes:
        #         t+=1
        #         response = self.send_message(f'Devuelve los personajes que aparecen en esta escena de un guion. La respuesta debe ser por cada personaje poner en una misma línea su nombre seguido de : y un resumen de las acciones que realiza en la escena y su estado de ánimo. Cada personaje va en una línea diferente sin líneas vacías entre ellos. Tu respuesta solo debe contar con lo especificado en este mensaje. Escena {scene.number} {scene.in_out} {scene.place} {scene.moment} Contenido de la escena según guion: {scene.text}')
        #         if response:
        #             characters = response.split('\n')
        #             for character_info in characters:
        #                 character_info = character_info.split(':')
        #                 current_amount = 1
        #                 if character_info[0].strip() in scene.characters.keys():
        #                     scene.characters[character_info[0].strip()].count += 1
        #                     current_amount = scene.characters[character_info[0].strip()].count
        #                 else:
        #                     scene.characters[character_info[0].strip()] = Character(1,character_info[1].strip())
        #                 if correct_answers_per_scene[scene.number - 1] < current_amount:
        #                     correct_answers_per_scene[scene.number - 1] = current_amount
        #                 print(t)
        # for scene in scenes:
        #     filtered_dict = {key: value for key, value in scene.character.items() if value.count >= correct_answers_per_scene[scene.number - 1]}
        #     scene.characters = filtered_dict
        i = 0
        count = 0
        while i < len(scenes):
            count+=1
            text = F"Devuelve los personajes que aparecen las escenas de un guion. T envío las escenas de la {i} hasta la {count*scene_amount_per_query}, son {scene_amount_per_query} escenas. Cada escena empieza con número de escena, interior o exterior, lugar y momento con el contenido de la escena del cual debes extraer los personajes. La respuesta debe ser por cada personaje poner en una misma línea su nombre seguido de : y una razón que para ti justifique su presencia en la escena. Es importante que no escribas los nombres de los mismos personajes más de una vez en la misma escena, si ves algo que haga referencia a los personajes como un grupo tampoco lo debes escribir como un nuevo personaje. Tu respuesta solo debe contar con lo especificado en este mensaje. Guion:"
            while i<count*scene_amount_per_query and (i < len(scenes)):
                text += f'Número de escena: {scenes[i].number} Interior/Exterior: {scenes[i].in_out} Lugar: {scenes[i].place} Momento: {scenes[i].moment} Contenido: {scenes[i].text} Fin de escena {scenes[i].number}\n'
                i+=1
            characters_responses = []
            for _ in range(query_amount):

                self.start_new_chat(instructions_characters)
                characters_responses.append(self.send_message(text))
            
            # time.sleep(30)
            if characters_responses:
                script_characters = self.aggregate_results(characters_responses,scenes, query_amount,i, script_characters)
    
        return script_characters

        
    def send_message(self, text, retry_count=0):
        # Get the characters from Gemini AI
        try:
            response = self.chat.send_message(text)
            return response.text.strip() if response else None
        except genai.types.BlockedPromptException as e:
            # Handle exception if the request is blocked
            print(f"The prompt was blocked: {e}")
            return None
        except ResourceExhausted as e:
            # Retry if resource limit is reached
            if retry_count < MAX_RETRIES:
                time.sleep(2 ** retry_count)  # Implement exponential backoff
                return self.send_message(text, retry_count + 1)
            else:
                raise e

    def aggregate_results(self, responses, scenes, query_amount, index, script_characters):

        # Process each response
        for response in responses:
            if response:
                for line in response.split('\n'):
                    if line.startswith('Escena'):
                        parts = line.split(': ')
                        characters_in_scene = set()
                        scene_number = int(parts[0].split()[1])
                        characters_info = parts[1].split('|')
                        if characters_info[len(characters_info)-1] == '':
                            characters_info.pop()
                        for char_info in characters_info:
                            try:
                                char_parts = char_info.split('-')
                                character = char_parts[0].strip()
                                reason = char_parts[1].strip()
                            except:
                                continue
                            if character in scenes[scene_number-1].characters.keys():
                                scenes[scene_number-1].characters[character].count +=1
                            else:
                                 scenes[scene_number-1].characters[character] = Character(1,reason)
        tmp = index - scene_amount_per_query
        remainder = divmod(len(scenes), scene_amount_per_query)[0]
        if remainder:
            tmp = index - remainder
        while tmp < index:
            filtered_dict = {key: value for key, value in scenes[tmp].characters.items() if value.count >= (query_amount/2)}
            scenes[tmp].characters = filtered_dict
            for character in list(scenes[tmp].characters.keys()):
                script_characters.add(character)
            tmp+=1

        return script_characters

    def set_continuity(self, scenes, query_amount):
        i = 0
        count = 0
        while i < len(scenes):
            count+=1
            text = "Por cada escena del guion que te mandaré a continuación devuelve la continuidad entre escenas.La respuesta debe ser por cada escena escribir por cada personaje que apararece en ella de qué escena viene y a qué escena va (en caso de no saber poner X1 o X2 si es la escena de la que viene o a la que se va respectivamente). La continuidad se refiere a la continuidad de vestuario y maquillaje de los actores que interpretarán al personaje, luego una escena va hacia otra si el personaje tiene que mantener el mismo aspecto entre ambas. La respuesta debe ser exactamente en el formato: Escena número de escena: Personaje1 = Escena de la que viene - Escena a la que va | Personaje2 = Escena de la que viene - Escena a la que va . No escribas nada adicional en tu respuesta excepto por lo especificado en el formato."
            while i<count*scene_amount_per_query and (i < len(scenes)):
                text += f'Escena {scenes[i].number} {scenes[i].in_out} {scenes[i].place} {scenes[i].moment} Personajes:{scenes[i].characters} Contenido: {scenes[i].text}\n'
                i+=1
            continuity_responses = []
            while not continuity_responses:
                for _ in range(query_amount):

                    self.start_new_chat(system_instructions_continuity)
                    continuity_responses.append(self.send_message(text))
            
                time.sleep(10)
            self.process_continuity_results(continuity_responses, scenes, i, query_amount)
    
    def process_continuity_results(self, responses, scenes, index, query_amount):
        # Process each response
        for response in responses:
            if response:
                for line in response.split('\n'):
                    if line.startswith('Escena'):
                        continuity_per_character = set()
                        parts = line.split(': ')
                        scene_number = int(parts[0].split()[1])
                        characters_info = parts[1].split('|')
                        if characters_info[len(characters_info)-1] == '':
                            characters_info.pop()
                        for char_info in characters_info:
                            try:
                                char_parts = char_info.split('=')
                                continuity = char_parts[1].split('-')
                                continuity_per_character.add(continuity[0].strip())
                                continuity_per_character.add(continuity[1].strip())
                            except:
                                continue
                        for element in continuity_per_character:
                            if element in scenes[scene_number - 1].continuity.keys():
                                scenes[scene_number - 1].continuity[element] +=1
                            else:
                                scenes[scene_number - 1].continuity[element] = 1
        tmp = index - scene_amount_per_query
        remainder = divmod(len(scenes), scene_amount_per_query)[0]
        if remainder:
            tmp = index - remainder
        while tmp < index:
            # Initialize your dictionaries
            dict = {
                    "previous": [],
                    "following": []
                    }
            # Iterate through the continuity dictionary
            for key, value in scenes[tmp].continuity.items():
                a = query_amount/2
                if value > query_amount/2:
                    if (key.isdigit() and int(key) < (scenes[tmp].number)):
                         dict["previous"].append(key)
                    elif (key.isdigit() and int(key) > (scenes[tmp].number)):
                        dict["following"].append(key)
            scenes[tmp].continuity = dict
            tmp+=1




if __name__ == "__main__":
    extractor = CharacterExtractor()
    text = ""
    for scene in scenes:
        text += f'Escena {scene.number}  {scene.in_out} {scene.moment} Contenido: {scene.text}\n'
    script_characters = extractor.set_continuity(scenes, 10)
    print("Ok")
