from pathlib import Path
import tempfile
import unittest
from digital_human.alignment import read_transcript,whisper_tokens,captions_from_tokens
from digital_human.storage import WorkflowError

class TranscriptEncoding(unittest.TestCase):
    def test_incomplete_punctuation_does_not_crash_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'tokens.json'
            p.write_bytes(b'{"transcription":[{"tokens":[{"text":"'+b'\xef\xbc'+ '你好'.encode()+b'","t_dtw":30}]}]}')
            text,times=whisper_tokens(read_transcript(p))
            self.assertEqual(text,'你好')
            self.assertEqual(captions_from_tokens('你好。',text,times,1.5)[0]['start'],.2)

    def test_incomplete_word_never_invents_missing_character(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'tokens.json'
            p.write_bytes(b'{"transcription":[{"tokens":[{"text":"'+ '你'.encode()+b'\xe5\xa5'+b'","t_dtw":30}]}]}')
            text,times=whisper_tokens(read_transcript(p))
            with self.assertRaises(WorkflowError):captions_from_tokens('你好。',text,times,1.5)

if __name__=='__main__':unittest.main()
