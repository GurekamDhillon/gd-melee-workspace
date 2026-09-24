// Lang.cs - the launcher's languages. Every string a player sees goes through L.T (plain text),
// L.F (a string.Format pattern) or, for tables built before the language is known, L.N (marks an
// English key; translated where it is shown). The KEY IS THE ENGLISH TEXT: English needs no table,
// and a missing Spanish entry falls back to English instead of failing.
//
// language= in launcher.cfg: auto (Windows display language: Spanish when it is "es", else English),
// en or es. It applies at the next start of the launcher.
//
// tools/release/launcher/check_strings.py checks that every key used in the sources has a Spanish
// entry with the same {n} placeholders and that no key is listed twice (a duplicate would throw
// when this class loads).
//
// Spanish terms, used consistently: mando (controller), adaptador de GameCube, imagen de disco (disc
// image), registro (log), informe de fallo (crash report), escenario (stage), personaje (character /
// fighter), servidor de emparejamiento (matchmaking server), partidas guardadas (saves). Informal
// "tú". Game menu names stay in English because the game itself is in English.

using System;
using System.Collections.Generic;
using System.Globalization;

namespace GDMelee
{
    static class L
    {
        public static bool Es;

        // setting: "auto" | "en" | "es"
        public static void Apply(string setting)
        {
            if (setting == "es") Es = true;
            else if (setting == "en") Es = false;
            else
            {
                string two = "";
                try { two = CultureInfo.CurrentUICulture.TwoLetterISOLanguageName; } catch { }
                Es = two == "es";
            }
        }

        public static string T(string en)
        {
            if (!Es || en == null) return en;
            string es;
            return Spanish.TryGetValue(en, out es) ? es : en;
        }

        public static string F(string en, params object[] args)
        {
            try { return string.Format(T(en), args); }
            catch (FormatException) { return string.Format(en, args); }
        }

        public static string N(string en) { return en; }

        // Disc kinds are stored in English in launcher.cfg ("ACE (m-ex mod)"); shown translated.
        public static string Kind(string kind)
        {
            if (kind == null) return "";
            if (kind.StartsWith("m-ex mod: ")) return T("m-ex mod: ") + kind.Substring(10);
            if (kind.StartsWith("Melee 1.02 mod: ")) return T("Melee 1.02 mod: ") + kind.Substring(16);
            return T(kind);
        }

        static readonly Dictionary<string, string> Spanish = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            // --- disc kinds and disc checks ---
            { "ACE (m-ex mod)", "ACE (mod de m-ex)" },
            { "Akaneia (m-ex mod)", "Akaneia (mod de m-ex)" },
            { "Melee 1.02 (vanilla)", "Melee 1.02 (vanilla)" },
            { "Melee 1.02 (modified)", "Melee 1.02 (modificado)" },
            { "Training Mode (TM-CE)", "Training Mode (TM-CE)" },
            { "m-ex mod: ", "mod de m-ex: " },
            { "Melee 1.02 mod: ", "mod de Melee 1.02: " },
            { "Game ID: {0}   revision: {1}\r\nTitle: {2}\r\n", "ID del juego: {0}   revisión: {1}\r\nTítulo: {2}\r\n" },
            { "Files on disc: {0}   size: {1:0.00} GB\r\n", "Archivos en el disco: {0}   tamaño: {1:0.00} GB\r\n" },
            { "Detected: {0}\r\n", "Detectado: {0}\r\n" },
            { "The file is too small to be a GameCube disc image.", "El archivo es demasiado pequeño para ser una imagen de disco de GameCube." },
            { "This is a compressed Dolphin image ({0}). GD's Melee reads plain disc images.\r\nIn Dolphin: right-click the game > Convert File... > Format: ISO, then pick the .iso.",
              "Esta es una imagen comprimida de Dolphin ({0}). GD's Melee lee imágenes de disco sin comprimir.\r\nEn Dolphin: clic derecho en el juego > Convertir archivo... > Formato: ISO, y luego elige el .iso." },
            { "This is a compressed CISO image. Convert it to a plain .iso first (Dolphin: Convert File... > ISO).",
              "Esta es una imagen CISO comprimida. Primero conviértela a un .iso normal (Dolphin: Convertir archivo... > ISO)." },
            { "This is a Wii disc image, not a GameCube one.", "Esta es una imagen de disco de Wii, no de GameCube." },
            { "This is not a GameCube disc image (the disc header's magic number is missing).",
              "Esto no es una imagen de disco de GameCube (falta el número mágico de la cabecera del disco)." },
            { "This disc is \"{0}\" ({1}), not Super Smash Bros. Melee.", "Este disco es \"{0}\" ({1}), no Super Smash Bros. Melee." },
            { "PAL (Europe)", "PAL (Europa)" },
            { "Japanese", "japonesa" },
            { "This is the {0} version of Melee. GD's Melee needs the NTSC-U (USA) disc, game ID GALE01.",
              "Esta es la versión {0} de Melee. GD's Melee necesita el disco NTSC-U (EE. UU.), ID del juego GALE01." },
            { "This is Melee NTSC 1.0{0}. GD's Melee needs revision 1.02 (the last USA revision, and the one every mod builds on).",
              "Este es Melee NTSC 1.0{0}. GD's Melee necesita la revisión 1.02 (la última de EE. UU., y la base de todos los mods)." },
            { "The disc's file table is unreadable. The image may be truncated or damaged; dump it again.",
              "No se puede leer la tabla de archivos del disco. La imagen puede estar incompleta o dañada; vuelve a extraerla." },
            { "This is an m-ex mod disc other than ACE or Akaneia. It may work, but only ACE and Akaneia are tested.",
              "Este es un disco de mod de m-ex distinto de ACE o Akaneia. Puede funcionar, pero solo ACE y Akaneia están probados." },
            { "The disc is Melee 1.02 but its files differ from the retail disc. Mods that patch the game's code may not work.",
              "El disco es Melee 1.02, pero sus archivos no coinciden con el disco original. Los mods que modifican el código del juego pueden no funcionar." },
            { "This disc boots, but its special features (the training lab and its menus) aren't supported yet: it plays like vanilla Melee for now.",
              "Este disco arranca, pero sus funciones especiales (el laboratorio de entrenamiento y sus menús) aún no son compatibles: por ahora se juega como Melee vanilla." },
            { "This disc boots, but its special features (the 20XX menus and codes) aren't supported yet: it plays like vanilla Melee for now.",
              "Este disco arranca, pero sus funciones especiales (los menús y códigos de 20XX) aún no son compatibles: por ahora se juega como Melee vanilla." },
            { "This is a mod built on Melee 1.02. Most mods patch the game's code, which GD's Melee does not run; expect it to behave like vanilla or to fail. Tested: vanilla 1.02, ACE, Akaneia.",
              "Este es un mod basado en Melee 1.02. La mayoría de los mods modifican el código del juego, que GD's Melee no ejecuta; lo normal es que se comporte como vanilla o que falle. Probados: vanilla 1.02, ACE, Akaneia." },
            { "This is an NKit image. If the game fails to start, restore it to a full ISO with NKit.",
              "Esta es una imagen NKit. Si el juego no arranca, restáurala a una ISO completa con NKit." },
            { "Could not read the file: {0}", "No se pudo leer el archivo: {0}" },
            { "development build", "versión de desarrollo" },

            // --- Diagnostics: categories and traces ---
            { "Watchdog samples", "Muestras del watchdog" },
            { "Where the game thread is, sampled ten times a second (\"gw: at ...\"), and a stats line every 2 s. Helps with freezes and silent exits.",
              "Dónde está el hilo del juego, muestreado diez veces por segundo (\"gw: at ...\"), y una línea de estadísticas cada 2 s. Sirve para congelamientos y cierres sin mensaje." },
            { "m-ex internals", "Detalles internos de m-ex" },
            { "Fighter and stage code from m-ex discs and mods: hooks installed, calls into their code, item and effect registration. For crashes with ACE/Akaneia fighters or stages.",
              "Código de personajes y escenarios de discos y mods de m-ex: ganchos instalados, llamadas a su código, registro de objetos y efectos. Para fallos con personajes o escenarios de ACE/Akaneia." },
            { "Memory (heap) trace", "Traza de memoria (heap)" },
            { "Every allocation from the game's heaps (MELEE_HEAP_TRACE). For \"out of memory\" / ALLOC_FAIL crashes. Large.",
              "Cada reserva de memoria de los heaps del juego (MELEE_HEAP_TRACE). Para fallos de \"memoria insuficiente\" / ALLOC_FAIL. Genera mucho texto." },
            { "Disc file trace", "Traza de archivos del disco" },
            { "Every file the game opens and where it came from, the disc or a mod (MELEE_DVD_TRACE). For missing or wrong files in mods.",
              "Cada archivo que abre el juego y de dónde viene, del disco o de un mod (MELEE_DVD_TRACE). Para archivos que faltan o están mal en los mods." },
            { "UI texture loads", "Carga de texturas de la interfaz" },
            { "Every menu texture the game opens (gxtex).", "Cada textura de menú que abre el juego (gxtex)." },
            { "Menu layout files", "Archivos de diseño de menús" },
            { "Sizes of the menu layout and animation files as they load.", "Tamaños de los archivos de diseño y animación de los menús al cargarse." },
            { "Sound bank loads", "Carga de bancos de sonido" },
            { "Each sound bank as it is loaded (synth: bank ...).", "Cada banco de sonido al cargarse (synth: bank ...)." },
            { "Rollback snapshot internals", "Detalles internos de las capturas de rollback" },
            { "Object pool bookkeeping inside rollback snapshots. For online desyncs, when asked.",
              "Contabilidad de los grupos de objetos dentro de las capturas de rollback. Para desincronizaciones en línea, si te lo piden." },
            { "Rollback log (MELEE_RB_LOG)", "Registro de rollback (MELEE_RB_LOG)" },
            { "Rollback and netplay frame decisions: rollbacks, input arrival, desync checks. For online problems.",
              "Decisiones de rollback y netplay por frame: rollbacks, llegada de entradas, comprobaciones de desincronización. Para problemas en línea." },
            { "Stage code trace (MELEE_GR_TRACE)", "Traza del código de escenarios (MELEE_GR_TRACE)" },
            { "Every call into an m-ex stage's own code. Very large; for a stage that crashes.",
              "Cada llamada al código propio de un escenario de m-ex. Genera muchísimo texto; para un escenario que falla." },
            { "m-ex engine call trace (MELEE_MEX_TRACE_CALLS)", "Traza de llamadas al motor de m-ex (MELEE_MEX_TRACE_CALLS)" },
            { "The first engine calls an m-ex fighter or stage makes, with arguments.",
              "Las primeras llamadas al motor que hace un personaje o escenario de m-ex, con sus argumentos." },
            { "Memory card diagnostics (MELEE_CARD_DIAG)", "Diagnóstico de la tarjeta de memoria (MELEE_CARD_DIAG)" },
            { "Saves and loads of the memory card files. For lost settings or saves.",
              "Guardado y carga de los archivos de la tarjeta de memoria. Para ajustes o partidas guardadas que se pierden." },
            { "Frame timing profile (MELEE_PROFILE)", "Perfil de tiempo por frame (MELEE_PROFILE)" },
            { "Where each frame's time goes, every 600 frames. For stutter or low frame rate.",
              "En qué se va el tiempo de cada frame, cada 600 frames. Para tirones o pocos FPS." },
            { "Show the frame rate (MELEE_SHOW_FPS)", "Mostrar los FPS (MELEE_SHOW_FPS)" },
            { "An FPS counter on the game window.", "Un contador de FPS en la ventana del juego." },
            { "Renderer log (MELEE_AURORA_VERBOSE)", "Registro del renderizador (MELEE_AURORA_VERBOSE)" },
            { "The graphics backend's own messages. For a black or broken screen.",
              "Los mensajes propios del motor gráfico. Para una pantalla negra o que se ve mal." },
            { "Report format trace (MELEE_PC_TRACE_OSREPORT)", "Traza de formatos de mensajes (MELEE_PC_TRACE_OSREPORT)" },
            { "Every game report's format string before it is printed. Doubles the log; for a crash inside logging.",
              "La cadena de formato de cada mensaje del juego antes de imprimirlo. Duplica el registro; para un fallo dentro del propio registro." },
            { "pad diagnostics {0}", "diagnóstico de mandos {0}" },
            { "release adapter on focus loss: on", "soltar el adaptador al perder el foco: sí" },
            { "release adapter on focus loss: off", "soltar el adaptador al perder el foco: no" },
            { "Diagnostics: the game's defaults.", "Diagnóstico: los valores predeterminados del juego." },
            { "Diagnostics on: {0}.", "Diagnóstico activado: {0}." },

            // --- crash reports ---
            { "no matchmaking server is set (netplay_server.txt)", "no hay ningún servidor de emparejamiento configurado (netplay_server.txt)" },
            { "the report is over 64 KB", "el informe pasa de 64 KB" },
            { "the server answered {0}", "el servidor respondió {0}" },
            { "no crash reports to send (in {0})", "no hay informes de fallo que enviar (en {0})" },
            { "sent 1 crash report", "se envió 1 informe de fallo" },
            { "sent {0} crash reports", "se enviaron {0} informes de fallo" },
            { "sent {0} of {1}, then failed: {2}", "se enviaron {0} de {1} y luego falló: {2}" },

            // --- main window ---
            { "Missing game files: {0}. Unzip the whole release again.", "Faltan archivos del juego: {0}. Vuelve a descomprimir la versión completa." },
            { "Ready.", "Listo." },
            { "Play", "Jugar" },
            { "Online", "En línea" },
            { "Mods", "Mods" },
            { "Diagnostics", "Diagnóstico" },
            { "About", "Acerca de" },
            { "Disc", "Disco" },
            { "Detected", "Detectado" },
            { "File", "Archivo" },
            { "&Add disc...", "&Añadir disco..." },
            { "&Change ISO...", "&Cambiar ISO..." },
            { "&Rename...", "Cambiar &nombre..." },
            { "Make &default", "&Predeterminado" },
            { "&Forget", "&Olvidar" },
            { "Unlock every character and stage (your save is not changed)", "Desbloquear todos los personajes y escenarios (no cambia tu partida guardada)" },
            { "Skip the intro movie", "Saltar el video de introducción" },
            { "Close this launcher when the game starts", "Cerrar este launcher al iniciar el juego" },
            { "Game volume: {0}%", "Volumen del juego: {0}%" },
            { "Play with a controller: a GameCube adapter or any gamepad. The keyboard is for hotkeys only.", "Se juega con mando: un adaptador de GameCube o cualquier gamepad. El teclado es solo para atajos." },
            { "PLAY", "JUGAR" },
            { "FILE MISSING", "FALTA EL ARCHIVO" },
            { "No disc yet. Click \"Add disc...\" and pick your Melee .iso.", "Aún no hay ningún disco. Haz clic en \"Añadir disco...\" y elige tu .iso de Melee." },
            { "The file is gone. Use \"Change ISO...\" to point at its new place.\r\n", "El archivo ya no está. Usa \"Cambiar ISO...\" para indicar su nueva ubicación.\r\n" },
            { "Saves for this disc: {0}", "Partidas guardadas de este disco: {0}" },
            { "Could not save settings: {0}", "No se pudieron guardar los ajustes: {0}" },
            { "GameCube disc images (*.iso;*.gcm)|*.iso;*.gcm|All files (*.*)|*.*", "Imágenes de disco de GameCube (*.iso;*.gcm)|*.iso;*.gcm|Todos los archivos (*.*)|*.*" },
            { "This disc can't be used", "No se puede usar este disco" },
            { "Use it anyway?", "¿Usarlo de todos modos?" },
            { "Check this disc", "Revisa este disco" },
            { "That disc is already in the list: {0}", "Ese disco ya está en la lista: {0}" },
            { "Not added: {0}", "No se añadió: {0}" },
            { "Added {0}: {1}.", "Se añadió {0}: {1}." },
            { "Pick a Super Smash Bros. Melee disc image (NTSC 1.02, or an ACE/Akaneia build)", "Elige una imagen de disco de Super Smash Bros. Melee (NTSC 1.02, o una versión de ACE/Akaneia)" },
            { "Welcome to GD's Melee.\r\n\r\nGD's Melee contains no Nintendo game data. It runs from your own disc image of Super Smash Bros. Melee: NTSC-U (USA) revision 1.02, as a plain .iso (or an ACE / Akaneia build made from it).\r\n\r\nPick the file next. It is remembered; you can add more discs, change or forget them later.",
              "Te damos la bienvenida a GD's Melee.\r\n\r\nGD's Melee no incluye datos de juegos de Nintendo. Funciona con tu propia imagen de disco de Super Smash Bros. Melee: NTSC-U (EE. UU.) revisión 1.02, como un .iso normal (o una versión de ACE / Akaneia hecha a partir de ella).\r\n\r\nA continuación elige el archivo. Se recuerda; más adelante puedes añadir más discos, cambiarlos u olvidarlos." },
            { "GD's Melee - first run", "GD's Melee - primer inicio" },
            { "Pick the new disc image for \"{0}\"", "Elige la nueva imagen de disco para \"{0}\"" },
            { "{0} now boots {1} ({2}). Its saves are unchanged.", "{0} ahora arranca {1} ({2}). Sus partidas guardadas no cambian." },
            { "Rename disc", "Cambiar el nombre del disco" },
            { "Name shown in the list:", "Nombre que se muestra en la lista:" },
            { "{0} is the default (\"--play\" and double-click boot it).", "{0} es el predeterminado (\"--play\" y el doble clic lo arrancan)." },
            { "Forget \"{0}\"?\r\n\r\nThe disc image itself is not touched, and its saves stay in\r\n{1}", "¿Olvidar \"{0}\"?\r\n\r\nLa imagen de disco no se toca y sus partidas guardadas se quedan en\r\n{1}" },
            { "Forget disc", "Olvidar disco" },
            { "Forgot {0}.", "Se olvidó {0}." },
            { "These game files are missing next to the launcher:\r\n\r\n{0}\r\n\r\nUnzip the whole release into one folder.", "Faltan estos archivos del juego junto al launcher:\r\n\r\n{0}\r\n\r\nDescomprime la versión completa en una sola carpeta." },
            { "The disc image for \"{0}\" is no longer at\r\n{1}\r\n\r\nFind it now?", "La imagen de disco de \"{0}\" ya no está en\r\n{1}\r\n\r\n¿Buscarla ahora?" },
            { "Disc not found", "No se encontró el disco" },
            { "Running {0} ({1}).", "Ejecutando {0} ({1})." },
            { "Could not start melee-pc.exe:\r\n{0}", "No se pudo iniciar melee-pc.exe:\r\n{0}" },
            { "The game crashed after {0} s. Report: {1}", "El juego falló después de {0} s. Informe: {1}" },
            { " (exit code 0x{0})", " (código de salida 0x{0})" },
            { "The game stopped with an error{0}.\r\n\r\nA short crash report was written to\r\n{1}\r\n(the whole log is beside it, ending in -full.log).\r\n\r\nOpen the report?",
              "El juego se detuvo con un error{0}.\r\n\r\nSe escribió un informe de fallo breve en\r\n{1}\r\n(el registro completo está al lado, terminado en -full.log).\r\n\r\n¿Abrir el informe?" },
            { "The game closed.", "El juego se cerró." },
            { "The game stopped with an error (code 0x{0}) after {1} s.", "El juego se detuvo con un error (código 0x{0}) después de {1} s." },
            { "The game stopped with an error (exit code 0x{0}).\r\n\r\nIts log is {1} (crash logs are in the crashlogs folder beside it).\r\nOpen the log?",
              "El juego se detuvo con un error (código de salida 0x{0}).\r\n\r\nSu registro es {1} (los informes de fallo están en la carpeta crashlogs, al lado).\r\n¿Abrir el registro?" },
            { "No log yet: {0}", "Aún no hay registro: {0}" },
            { "OK", "Aceptar" },
            { "Cancel", "Cancelar" },

            // --- Online tab ---
            { "Online play is in the game: VERSUS > ONLINE (Host a Room, Join a Room, Random Opponent). Both players need this same release of GD's Melee. Mods are welcome online: any fighter or stage you both have can be picked (see the Mods tab).\r\n\r\nRoom codes (short codes instead of IP addresses) need a matchmaking server. Enter its address here as host:port, or leave it empty to swap addresses by hand. The setting is stored in netplay_server.txt next to the game.",
              "El juego en línea está dentro del juego: VERSUS > ONLINE (Host a Room, Join a Room, Random Opponent). Los dos jugadores necesitan esta misma versión de GD's Melee. Los mods son bienvenidos en línea: se puede elegir cualquier personaje o escenario que tengan los dos (mira la pestaña Mods).\r\n\r\nLos códigos de sala (códigos cortos en lugar de direcciones IP) necesitan un servidor de emparejamiento. Escribe aquí su dirección como host:puerto, o déjalo vacío para intercambiar direcciones a mano. El ajuste se guarda en netplay_server.txt junto al juego." },
            { "Matchmaking server (host:port):", "Servidor de emparejamiento (host:puerto):" },
            { "Save", "Guardar" },
            { "Clear", "Borrar" },
            { "How to play online", "Cómo jugar en línea" },
            { "Room codes use {0}.", "Los códigos de sala usan {0}." },
            { "No server set: players swap addresses (the ONLINE screen shows yours).", "No hay servidor: los jugadores intercambian direcciones (la pantalla ONLINE muestra la tuya)." },
            { "Write it as host:port, for example play.example.net:51500", "Escríbelo como host:puerto, por ejemplo play.example.net:51500" },
            { "Matchmaking server", "Servidor de emparejamiento" },
            { "Server setting saved.", "Se guardó el servidor." },
            { "Could not write {0}:\r\n{1}\r\n\r\nMove the game to a folder you can write to (not Program Files).",
              "No se pudo escribir {0}:\r\n{1}\r\n\r\nMueve el juego a una carpeta en la que puedas escribir (no Archivos de programa)." },

            // --- Diagnostics tab ---
            { "Changes apply the next time the game starts.", "Los cambios se aplican la próxima vez que inicies el juego." },
            { "The game writes melee-pc.log in its folder. By default it keeps it short: scene changes, fighter, stage and mod loads, warnings and errors, online and controller events. If you are asked for more detail for a bug report, turn on what you were asked for here, play until it happens, then send the log. Hover over an option for what it adds.",
              "El juego escribe melee-pc.log en su carpeta. Por defecto lo mantiene breve: cambios de escena, carga de personajes, escenarios y mods, avisos y errores, eventos en línea y de mandos. Si te piden más detalle para un reporte de error, activa aquí lo que te pidieron, juega hasta que ocurra y luego envía el registro. Pasa el ratón sobre una opción para ver qué añade." },
            { "Game log", "Registro del juego" },
            { "Scene changes and menu cursors (on by default)", "Cambios de escena y cursores de menú (activado por defecto)" },
            { "Every screen change and the menu cursor positions. Turn off only if asked.", "Cada cambio de pantalla y las posiciones del cursor en los menús. Desactívalo solo si te lo piden." },
            { "Rendering diagnostics (DIAG blocks):", "Diagnóstico de renderizado (bloques DIAG):" },
            { "The renderer's DIAG block: matrices, EFB copies, a depth grid and the camera. The first one after each scene change is enough to tell why a screen is black.",
              "El bloque DIAG del renderizador: matrices, copias del EFB, una rejilla de profundidad y la cámara. El primero tras cada cambio de escena basta para saber por qué una pantalla sale negra." },
            { "One block per scene (default)", "Un bloque por escena (predeterminado)" },
            { "Every block (every half second)", "Todos los bloques (cada medio segundo)" },
            { "None", "Ninguno" },
            { "Everything (MELEE_LOG=all)", "Todo (MELEE_LOG=all)" },
            { "Every line from every category above, no flood limit. The log gets large quickly.", "Cada línea de todas las categorías de arriba, sin límite. El registro crece muy rápido." },
            { "Controllers", "Mandos" },
            { "Controller diagnostics (MELEE_PAD_DIAG):", "Diagnóstico de mandos (MELEE_PAD_DIAG):" },
            { "What the game logs about controllers and the GameCube adapter. Level 1, the event log (plugged in, unplugged, device switches), is the game's default; level 2 adds the old verbose dump of every pad every 30 frames.",
              "Lo que el juego registra sobre los mandos y el adaptador de GameCube. El nivel 1, el registro de eventos (conectado, desconectado, cambios de dispositivo), es el predeterminado del juego; el nivel 2 añade el volcado detallado de cada mando cada 30 frames." },
            { "Game default (1, events)", "Predeterminado del juego (1, eventos)" },
            { "0 - off", "0 - desactivado" },
            { "1 - events: plug, unplug, device switches", "1 - eventos: conectar, desconectar, cambios de dispositivo" },
            { "2 - verbose: every pad every 30 frames (large)", "2 - detallado: cada mando cada 30 frames (mucho texto)" },
            { "Let go of the GameCube adapter when the game window loses focus (MELEE_PAD_RELEASE_ON_BLUR):", "Soltar el adaptador de GameCube cuando la ventana del juego pierde el foco (MELEE_PAD_RELEASE_ON_BLUR):" },
            { "On (the game's default): switching to another window hands the adapter to Dolphin or another copy of the game, and it is taken back when you return. Off: the game keeps it, as Dolphin does. During online play it is always kept.",
              "Sí (predeterminado del juego): al cambiar a otra ventana, el adaptador pasa a Dolphin o a otra copia del juego, y se recupera al volver. No: el juego se lo queda, como hace Dolphin. Durante el juego en línea siempre se lo queda." },
            { "Game default (on)", "Predeterminado del juego (sí)" },
            { "Off - keep the adapter", "No - quedarse el adaptador" },
            { "On - release it", "Sí - soltarlo" },
            { "Deeper traces (only when asked)", "Trazas más detalladas (solo si te lo piden)" },
            { "Crash reports", "Informes de fallo" },
            { "Upload last 3 crash logs", "Subir los 3 últimos informes de fallo" },
            { "Allow uploading crash reports", "Permitir subir informes de fallo" },
            { "Off by default. Nothing is ever sent on its own: only the button below sends anything.", "Desactivado por defecto. Nunca se envía nada por sí solo: solo el botón de abajo envía algo." },
            { "What is sent: the short crash reports the game writes to crashlogs (crash-<time>.log, at most 64 KB each) - the game version, the disc's ID and title, the mods you use, your settings, the error with the code it happened in, and the last lines of the log. Your Windows user name is removed from every path and your player name is left out; the full log (-full.log) is never sent.\r\nWhere: the matchmaking server this game uses for online play (netplay_server.txt).\r\nWhy: so crashes can be found and fixed without you having to send files by hand.\r\nNothing is sent automatically. The button sends your three newest reports (not faults that happened while the game was closing), once, when you click it.",
              "Qué se envía: los informes de fallo breves que el juego escribe en crashlogs (crash-<hora>.log, 64 KB como máximo cada uno): la versión del juego, el ID y el título del disco, los mods que usas, tus ajustes, el error con el código donde ocurrió y las últimas líneas del registro. Tu nombre de usuario de Windows se quita de todas las rutas y tu nombre de jugador no se incluye; el registro completo (-full.log) nunca se envía.\r\nA dónde: al servidor de emparejamiento que usa este juego para jugar en línea (netplay_server.txt).\r\nPara qué: para encontrar y corregir los fallos sin que tengas que enviar archivos a mano.\r\nNada se envía automáticamente. El botón envía tus tres informes más recientes (no los fallos ocurridos mientras el juego se cerraba), una vez, cuando haces clic." },
            { "Open log folder", "Abrir la carpeta del registro" },
            { "Open game log", "Abrir el registro del juego" },
            { "Open latest crash report", "Abrir el último informe de fallo" },
            { "Copy latest crash report", "Copiar el último informe de fallo" },
            { "Reset to defaults", "Restablecer valores" },
            { "Diagnostics are back to the game's defaults.", "El diagnóstico volvió a los valores predeterminados del juego." },
            { "No crash reports in {0}.", "No hay informes de fallo en {0}." },
            { "Copied {0} ({1} KB) to the clipboard.", "Se copió {0} ({1} KB) al portapapeles." },
            { "Could not copy the report: {0}", "No se pudo copiar el informe: {0}" },
            { "No matchmaking server is set (Online tab), so there is nowhere to send the reports.", "No hay ningún servidor de emparejamiento configurado (pestaña En línea), así que no hay a dónde enviar los informes." },
            { "Crash logs: {0}.", "Informes de fallo: {0}." },
            { "{0} to {1}. Thank you.", "{0} a {1}. ¡Gracias!" },
            { "{0}.", "{0}." },

            // --- About tab ---
            { "A native PC port of Super Smash Bros. Melee, built from the community decompilation.\r\n\r\nThis download contains no Nintendo game data: no disc image, no game files, no textures, music or models. Everything the game shows comes from the disc image you pick. Super Smash Bros. Melee is (c) Nintendo / HAL Laboratory; this project is not affiliated with or endorsed by them.\r\n\r\nLicences for the port and the libraries it uses are in the LICENSES folder.",
              "Un port nativo para PC de Super Smash Bros. Melee, hecho a partir de la decompilación de la comunidad.\r\n\r\nEsta descarga no contiene datos de juegos de Nintendo: ni imagen de disco, ni archivos del juego, ni texturas, música o modelos. Todo lo que muestra el juego sale de la imagen de disco que elijas. Super Smash Bros. Melee es (c) Nintendo / HAL Laboratory; este proyecto no está afiliado a ellos ni cuenta con su respaldo.\r\n\r\nLas licencias del port y de las bibliotecas que usa están en la carpeta LICENSES." },
            { "Open game folder", "Abrir la carpeta del juego" },
            { "Open saves folder", "Abrir la carpeta de partidas guardadas" },
            { "Licences", "Licencias" },
            { "Source code", "Código fuente" },
            { "Game folder: {0}\r\nSettings and saves: {1}", "Carpeta del juego: {0}\r\nAjustes y partidas guardadas: {1}" },
            { "Language:", "Idioma:" },
            { "Automatic (Windows language)", "Automático (idioma de Windows)" },
            { "The language changes the next time the launcher starts.", "El idioma cambia la próxima vez que inicies el launcher." },

            // --- Mods tab and browser ---
            { "(mod.json is not valid JSON)", "(mod.json no es un JSON válido)" },
            { "refusing {0}:// (only https downloads are allowed): {1}", "se rechaza {0}:// (solo se permiten descargas https): {1}" },
            { "the index is larger than {0} bytes", "el índice ocupa más de {0} bytes" },
            { "the download is larger than declared ({0} bytes)", "la descarga es más grande de lo declarado ({0} bytes)" },
            { "the download is larger than declared", "la descarga es más grande de lo declarado" },
            { "empty name", "nombre vacío" },
            { "a character that is not allowed in a file name", "un carácter no permitido en un nombre de archivo" },
            { "an absolute path", "una ruta absoluta" },
            { "a '..' step out of the folder", "un paso '..' fuera de la carpeta" },
            { "a '.' segment", "un segmento '.'" },
            { "a name ending in '.' or ' '", "un nombre que termina en '.' o ' '" },
            { "a reserved device name ({0})", "un nombre de dispositivo reservado ({0})" },
            { "unsafe entry \"{0}\" in the zip: {1}", "entrada insegura \"{0}\" en el zip: {1}" },
            { "the zip contains a symbolic link ({0})", "el zip contiene un enlace simbólico ({0})" },
            { "the zip unpacks to more than 3 GB", "el zip ocupa más de 3 GB al descomprimirse" },
            { "zip entry escapes the mod folder: {0}", "una entrada del zip sale de la carpeta del mod: {0}" },
            { "not a GitHub repo or a URL", "no es un repositorio de GitHub ni una URL" },
            { "the index is not valid JSON ({0})", "el índice no es un JSON válido ({0})" },
            { "the index has no \"mods\" list", "el índice no tiene una lista \"mods\"" },
            { "skipped a mod with a bad id \"{0}\" (lower-case letters, digits, . _ -)", "se omitió un mod con un id no válido \"{0}\" (letras minúsculas, dígitos, . _ -)" },
            { "skipped {0}: it needs url, sha256 and size", "se omitió {0}: necesita url, sha256 y size" },
            { "the index lists no mods", "el índice no incluye ningún mod" },
            { "bad mod id {0}", "id de mod no válido: {0}" },
            { "{0} needs scripting API {1}; this game has {2}. Update GD's Melee first.", "{0} necesita la API de scripts {1}; este juego tiene la {2}. Primero actualiza GD's Melee." },
            { "the download is {0} bytes; the index says {1}", "la descarga ocupa {0} bytes; el índice dice {1}" },
            { "the download's sha256 does not match the index - not installed", "el sha256 de la descarga no coincide con el índice; no se instaló" },
            { "the zip has no mod.json at its top level", "el zip no tiene un mod.json en su nivel superior" },
            { "the zip's mod.json says id \"{0}\", the index says \"{1}\"", "el mod.json del zip dice id \"{0}\", el índice dice \"{1}\"" },
            { "Installed mod", "Mod instalado" },
            { "Version", "Versión" },
            { "Kind", "Tipo" },
            { "Needs", "Requiere" },
            { "Available mod", "Mod disponible" },
            { "Status", "Estado" },
            { "Source", "Fuente" },
            { "Remove", "Quitar" },
            { "Open mods folder", "Abrir la carpeta de mods" },
            { "Refresh sources", "Actualizar fuentes" },
            { "Install", "Instalar" },
            { "Reinstall", "Reinstalar" },
            { "Update", "Actualizar" },
            { "Edit sources...", "Editar fuentes..." },
            { "Console socket for tools (127.0.0.1:51700)", "Socket de consola para herramientas (127.0.0.1:51700)" },
            { "Open scripts folder", "Abrir la carpeta de scripts" },
            { "No sources yet: \"Edit sources...\" to add the ones you trust.", "Aún no hay fuentes: usa \"Editar fuentes...\" para añadir las que te den confianza." },
            { "{0} source(s). \"Refresh sources\" to see their mods.", "{0} fuente(s). Usa \"Actualizar fuentes\" para ver sus mods." },
            { "  (pack {0})", "  (paquete {0})" },
            { "  by {0}", "  de {0}" },
            { "Needs: {0}    Conflicts with: {1}", "Requiere: {0}    Choca con: {1}" },
            { "MISSING {0}", "FALTA {0}" },
            { "installed", "instalado" },
            { "update {0} > {1}", "actualizar {0} > {1}" },
            { "Enabled {0} for the next start of the game.", "{0} activado para el próximo inicio del juego." },
            { "Disabled {0} for the next start of the game.", "{0} desactivado para el próximo inicio del juego." },
            { "Remove {0}? Its folder is deleted.", "¿Quitar {0}? Se borra su carpeta." },
            { "\r\n\r\nThese installed mods need it: {0}", "\r\n\r\nEstos mods instalados lo necesitan: {0}" },
            { "Remove mod", "Quitar mod" },
            { "Removed {0}.", "Se quitó {0}." },
            { "Could not remove {0}:\r\n{1}", "No se pudo quitar {0}:\r\n{1}" },
            { "No sources in mods\\sources.txt - \"Edit sources...\" to add some.", "No hay fuentes en mods\\sources.txt: usa \"Editar fuentes...\" para añadir alguna." },
            { "Reading {0} source(s)...", "Leyendo {0} fuente(s)..." },
            { "{0} mod(s) from {1} source(s)", "{0} mod(s) de {1} fuente(s)" },
            { " - {0} problem(s)", " - {0} problema(s)" },
            { "Mod sources", "Fuentes de mods" },
            { "{0} (conflicts with {1})", "{0} (choca con {1})" },
            { "Install {0} {1}?", "¿Instalar {0} {1}?" },
            { "From: {0}", "Desde: {0}" },
            { "It needs, and these are installed too:", "Lo necesita, y también se instalan:" },
            { "It needs mods none of your sources offer: {0}. It will not load without them.", "Necesita mods que ninguna de tus fuentes ofrece: {0}. No se cargará sin ellos." },
            { "These enabled mods conflict and will be disabled: {0}", "Estos mods activados chocan y se desactivarán: {0}" },
            { "Mods are other people's work: install the ones you trust. Downloads are checked against the source's sha256; nothing downloaded is run by the launcher.",
              "Los mods son trabajo de otras personas: instala los que te den confianza. Las descargas se comprueban con el sha256 de la fuente; el launcher no ejecuta nada de lo que descarga." },
            { "Install mod", "Instalar mod" },
            { "Downloading {0}...", "Descargando {0}..." },
            { "Install failed.", "La instalación falló." },
            { "Not installed - {0}", "No se instaló: {0}" },
            { "Installed {0}. It loads at the next start of the game.", "Se instaló {0}. Se carga en el próximo inicio del juego." },
        };
    }
}
