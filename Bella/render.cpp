/**
Audio onset detection using energy of the signal
-----------------------------------------------
The script reads audio samples (currently only from one input) into a buffer and 
for every hopSize it calculates the energy of the buffer. If energy is higher than
the energyThreshold it activates the digital pin if it is not in the refractory period 
*/

#include <Bela.h>
#include <cmath>
#include <vector>
#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <libraries/AudioFile/AudioFile.h>
#include <libraries/Biquad/Biquad.h>
#include <algorithm>
#include <ctime>
#include <libraries/Scope/Scope.h>

// Create a scope object with 2 channels
Scope scope;

// config file 
const std::string configFilename = "config.txt"; 

// configuration parameters
int bufferSize = 512; 							// num of samples stored in buffer for energy calculation
int hopSize = 256;			 					// interval at which buffer is processed
float refractoryPeriod = 0.5;					// refractory period (sec)
float activationDuration = 0.05;				// duration to activate the digital output pin after onset detection (sec)
float inputGain = 55;							// input gain for the microphones 	
float energyThreshold = 0.001;					// threshold for detecting an onset
float toneFreq = 200.0;

// state variables
std::vector<float> audioBuffer(bufferSize, 0.0f);
int bufferIndex = 0;							// current position in audioBuffer
int hopCounter = 0;								// to track samples processed since last energy calculation 
int refractoryPeriodSamples;
int refractoryCounter = 0;						// to track refractory period
int timeSinceLastOnset = 0; 					// to track samples since last onset
int activationDurationSamples;
int activationCounter = 0;						// to track how long digital output is activated
const int digitalPin = 0;						// digital pin number to activate

// recording audio variables
std::vector<std::vector<float>> audioRecorder;	// variable to save audio
std::string audioFilename;						// filename to save audio
std::vector<int>digitalPinRecorder;				// variable to save digital pin states for the marker events 
std::string markerFilename;						// filename to save markers from the digital pin
double recordAudio = 0;							// recording duration in sec 
double recordDuration = 20;						// recording duration in sec 
unsigned int recordingFrames = 0;				// to track the frames recorded


// function to generate a unique filename (adds the current timestamp)
std::string generateFilename(const std::string& baseFilename){
	std::time_t now = std::time(nullptr);
	char timestamp[20];
	std::strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", std::localtime(&now));
	return baseFilename + "_" + timestamp;
}

// function to read from config file 
bool readConfig(const std::string& filename){
	// opening config file 
	std::ifstream configFile(filename);
	// throw error if config file cannot be opened 
	if(!configFile.is_open()){
		rt_printf("Cannot open the config file");
		return false;
	}
	
	std::string line;
	// reading each line in the config file 
	while(std::getline(configFile, line)){
		std::istringstream iss(line);
		std::string key;
		// looking for energy threshold key in config 
		if(iss >> key){
			if(key == "energyThreshold"){
				// read and parse energy threshold value
				if(!(iss >> energyThreshold)){
					rt_printf("Error reading energy threshold value\n");
					return false;
				}
			// looking for record on/off key in config 
			} else if(key == "recordAudio"){
				// read and parse record duration value
				if(!(iss >> recordAudio)){
						rt_printf("Error reading recording on/off value\n");
					return false;
				}
			// looking for record duration key in config
			} else if(key == "recordDuration"){
				// read and parse record duration value
				if(!(iss >> recordDuration)){
						rt_printf("Error reading recording duration value\n");
					return false;
				}
			// looking for input gain key in config
			}else if(key == "inputGain"){
				// read and parse record duration value
				if(!(iss >> inputGain)){
						rt_printf("Error reading input gain value\n");
					return false;
				}
			}
		} 
	}
	
	// closing config file
	configFile.close();
	return true;
}

// function to calculate energy of a buffer
float calculateEnergy(const std::vector<float>& buffer) {
	float energy = 0.0f;
	for (const auto& sample : buffer) {
		energy += sample * sample;
	}
	return energy / buffer.size();
}

// function to setup
bool setup(BelaContext *context, void *userData) {
	    // Initialize scope with 2 channels at the audio sample rate
     scope.setup(2, context->audioSampleRate);

	// setting input gain for left and right
	Bela_setAudioInputGain(0, inputGain);			
	Bela_setAudioInputGain(1, inputGain);
	
	// converting to samples
	refractoryPeriodSamples = context->audioSampleRate * refractoryPeriod;
	activationDurationSamples = context->audioSampleRate * activationDuration;
	
	// seting digital pin as output pin
	pinMode(context, 0, digitalPin, OUTPUT);   
	
	// read config file 
	if(!readConfig(configFilename)){
		rt_printf("Using default energy threshold value: %f\n", energyThreshold);
		rt_printf("Using default recording duration value: %f\n", recordDuration);
		rt_printf("Using default input gain value: %f\n", inputGain);
	} else {
		rt_printf("Using energy threshold value from config file: %f\n", energyThreshold);
		rt_printf("Using recording duration value from config file: %f\n", recordDuration);
		rt_printf("Using input gain value from config file: %f\n", inputGain);
	}
	
	// audio recording status
	if(recordAudio == 1){
		// generate file name for audio file
		audioFilename = generateFilename("audiofile") + ".wav";
		rt_printf("Audio recording is ON. Recording to file: %s\n", audioFilename.c_str());
		// generate file name for markers 
		markerFilename = generateFilename("markerfile") + ".txt";
		rt_printf("Audio Marker file: %s\n", markerFilename.c_str());
		
	} else if(recordAudio == 0){
		rt_printf("Audio recording is OFF\n");
	}
	
	// allocate memory to store audio
	unsigned int numFrames = context->audioSampleRate * recordDuration;
	audioRecorder.resize(context->audioInChannels);
	digitalPinRecorder.resize(numFrames);
	try {
		for(auto& c : audioRecorder)
			c.resize(numFrames);
	} catch (std::exception& e){
		fprintf(stderr, "Error while allocating memory.");
		return false;
	}
	return true;
}

// function to render new audio samples
void render(BelaContext *context, void *userData) {
	static float phase = 0.0f;
	float phaseIncrement = 2.0f * M_PI * toneFreq / context->audioSampleRate;
	
	// loop over each sample
	for (unsigned int n = 0; n < context->audioFrames; ++n) {
		float micInputL = audioRead(context, n, 0);  // Left microphone (channel 0)
        float micInputR = audioRead(context, n, 1);  // Right microphone (channel 1)

        // Send both channels to the scope
        scope.log(micInputL, micInputR);
	
		// read the current sample from the input channel 0
		float currentSample = audioRead(context, n, 0);
		
	    // update the buffer with the current sample
	    audioBuffer[bufferIndex] = currentSample;
	    bufferIndex = (bufferIndex + 1) % bufferSize;
	
	    // increment hop counter
	    hopCounter++;
	    // wainitng until hopSize is reached  
	    if (hopCounter >= hopSize) {
	    	// reset hopCounter
	        hopCounter = 0;
	
	        // calculate energy
	        float energy = calculateEnergy(audioBuffer);
	        // Print the energy value to the command line
	        //rt_printf("Energy: %f\n", energy);

	        // check for energy-based onset detection
	        if (energy >= energyThreshold && refractoryCounter <= 0) {
	            rt_printf("Onset detected! Energy: %f\n", energy);
	            rt_printf("Time since last onset: %f seconds\n", timeSinceLastOnset / context->audioSampleRate);
	
	            refractoryCounter = refractoryPeriodSamples;		 // set the refractory counter
	            timeSinceLastOnset = 0;								 // reset the counter for time since last onset
	            activationCounter = activationDurationSamples;       // set the activation counter
	            digitalWrite(context, n, digitalPin, HIGH);          // activate the digital output pin
	             rt_printf("Pin On\n");
	        }
	    }
	    
	    // decrement the refractory counter if it's active
	    if (refractoryCounter > 0) {
	        refractoryCounter--;
	    }
	    
	    // increment the counter for time since last onset
	    timeSinceLastOnset++;
	    
	    // handle the digital output activation duration
	    if (activationCounter > 0) {
	        activationCounter--;
	        if (activationCounter == 0) {
	            digitalWrite(context, n, digitalPin, LOW);			  // deactivate the digital output pin
	            rt_printf("Pin Off\n");
	        }
	        
	        // send audio pulse to audio output pin when trigger detected
	        float out = sinf(phase);
	        phase += phaseIncrement;
	        if(phase >= 2.0f * M_PI){
	        	phase -= 2.0f * M_PI;
	        }
	        audioWrite(context, n, 0, out);
	        audioWrite(context, n, 1, out);
		} else {
			audioWrite(context, n, 0, 0.0f);
	        audioWrite(context, n, 1, 0.0f);
		}
		
		if(recordAudio == 1){
			// store current sample to record
			audioRecorder[0][recordingFrames] = currentSample;
			digitalPinRecorder[recordingFrames] = digitalRead(context, n, digitalPin);
			++recordingFrames;
			if(recordingFrames >= audioRecorder[0].size()){
				Bela_requestStop();
				return;
			}
		}
	}
}

void cleanup(BelaContext *context, void *userData) {
	for(auto& i : audioRecorder)
		i.resize(recordingFrames);
	digitalPinRecorder.resize(recordingFrames);
	if(recordAudio == 1){
		// saving the audio file
		AudioFileUtilities::write(audioFilename, audioRecorder, context->audioSampleRate);
		rt_printf("Audio recording saved\n");
		// saving the marker file
		std::ofstream markerFile(markerFilename);
		if(markerFile.is_open()){
			for(const auto& state : digitalPinRecorder){
				markerFile << state << "\n";
			}
			markerFile.close();
		}
		
	}
}


