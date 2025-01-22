import propar
import time

def main():
    # Connect to instrument
    instrument = propar.instrument('COM5')
    
    try:
        # Get setpoint from user
        setpoint = float(input("Enter setpoint (0-100%): "))
        
        # Convert to instrument scale (0-32000)
        setpoint_value = int((setpoint / 100.0) * 32000)
        instrument.writeParameter(9, setpoint_value)
        print("setpoint valueeee: " + setpoint_value)
        print("\nReading values (Ctrl+C to stop)...")
        while True:
            # Clear screen
            print("\033[2J\033[H")
            
            # Read parameters individually with error checking
            measure = instrument.read(33, 0, propar.PP_TYPE_FLOAT)
            valve = instrument.read(33, 1, propar.PP_TYPE_FLOAT)
            temp = instrument.read(33, 7, propar.PP_TYPE_FLOAT)
            
            # Display values with error checking
            print(f"Instrument Status:")
            print("-" * 50)
            print(f"Setpoint:         {setpoint:.1f}%")
            print(f"Flow measure:     {measure if measure is not None else 'N/A'}")
            print(f"Valve output:     {valve if valve is not None else 'N/A'}")
            print(f"Temperature:      {temp if temp is not None else 'N/A'}")
            print("-" * 50)
            print("Press Ctrl+C to stop")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping flow...")
        instrument.writeParameter(9, 0)  # Set flow to 0
        
    except ValueError:
        print("Invalid input - please enter a number between 0-100")

if __name__ == "__main__":
    main()