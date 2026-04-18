import serial
import time

PUERTO = 'COM5'     # Cambia esto por tu puerto Arduino
BAUDRATE = 9600

def main():
    try:
        arduino = serial.Serial(PUERTO, BAUDRATE, timeout=1)
        time.sleep(2)  # esperar a que Arduino reinicie

        print(f"Conectado a {PUERTO} a {BAUDRATE} baudios")
        print("Escribe un mensaje para enviarlo al Arduino.")
        print("Escribe 'salir' para terminar.\n")

        while True:
            mensaje = input("Enviar: ")

            if mensaje.lower() == "salir":
                break

            arduino.write((mensaje + '\n').encode('utf-8'))
            print(f"Enviado: {mensaje}")

            time.sleep(0.1)

            if arduino.in_waiting > 0:
                respuesta = arduino.readline().decode('utf-8').strip()
                print(f"Arduino respondió: {respuesta}")

        arduino.close()
        print("Puerto serial cerrado.")

    except serial.SerialException as e:
        print("Error al abrir el puerto serial:", e)

if __name__ == "__main__":
    main()