from synthesizer.inference import synthesizer
from encoder import inference as encoder
from vocoder import inference as vocoder
from pathlib import Path
import numpy as np
import librosa
import argparse
import torch
import sys

if __name__ == '__main__':
    ## Info & args
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("-e", "--enc_model_fpath", type=Path, default="encoder/saved_models/pretrained.pt", help="Path to a saved encoder")
    parser.add_argument("-s", "--syn_model_dir", type=Path, default="synthesizer/saved_models/logs-pretrained/", help="Directory containing the synthesizer model")
    parser.add_argument("-v", "--voc_model_fpath", type=Path, default="vocoder/saved_models/pretrained/pretrained.pt", help="Path to a saved vocoder")
    parser.add_argument("--out", type=Path, default="output.wav", help="sets the output wav file")
    parser.add_argument("--textin", type=Path, help="sets the output wav file")
    parser.add_argument("--voicein", type=Path, default="input.wav", help="sets the input wav file")

    args = parser.parse_args()

    print(f"Arguments:\nEncoder model path: {args.enc_model_fpath}\nSynthesizer model directory: {args.syn_model_dir}\nVocoder model path: {args.voc_model_fpath}")
    print(f"Output file: {args.out}\nText input file: {args.textin}\nVoice input file: {args.voicein}")
    
    ## Check for CUDA
    print("Running a test of your configuration...\n")
    if not torch.cuda.is_available():
        print("Your PyTorch installation is not configured to use CUDA. If you have a GPU ready for deep learning, ensure that the drivers are properly installed, and that your CUDA version matches your PyTorch installation. CPU-only inference is currently not supported.", file=sys.stderr)
        quit(-1)
    
    device_id = torch.cuda.current_device()
    gpu_properties = torch.cuda.get_device_properties(device_id)
    print(f"Found {torch.cuda.device_count()} GPUs available. Using GPU {device_id} ({gpu_properties.name}) with {gpu_properties.total_memory / 1e9}GB total memory.\n")
    
    ## Load models
    print("Preparing the encoder, synthesizer, and vocoder...")
    encoder.load_model(args.enc_model_fpath)
    synthesizer = Synthesizer(args.syn_model_dir.joinpath("taco_pretrained"))
    vocoder.load_model(args.voc_model_fpath)

    if args.voicein:
        in_fpath = args.voicein
    else:
        message = "Reference voice: enter an audio filepath of a voice to be cloned (mp3, wav, m4a, flac, ...):\n"
        in_fpath = Path(input(message).replace("\"", "").replace("\'", ""))

    print(f"Input voice file: {in_fpath}")

    embeds = [encoder.embed_utterance(encoder.preprocess_wav(in_fpath))]

    try:
        if args.textin:
            text = str(args.textin)
        else:
            text = input("Write a sentence (+-20 words) to be synthesized:\n")

        texts = [text]
        specs = synthesizer.synthesize_spectrograms(texts, embeds)
        spec = specs[0]
        print("Created mel spectrogram")

        print("Synthesizing waveform:")
        generated_wav = vocoder.infer_waveform(spec)

        generated_wav = np.pad(generated_wav, (0, synthesizer.sample_rate), mode="constant")

        output_file = args.out if args.out else "output.wav"
        print(f"Saving output as {output_file}")
        librosa.output.write_wav(output_file, generated_wav.astype(np.float32), synthesizer.sample_rate)

    except Exception as e:
        print(f"Caught exception: {repr(e)}")
        print("Restarting\n")
