import { analyze } from './parse-source.js';
import {
  decodeInput,
  encodeResult,
  MAX_INPUT_BYTES,
  ParseFailure,
  PROTOCOL_VERSION,
} from './protocol.js';

try {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > MAX_INPUT_BYTES) throw new ParseFailure('input_limit');
    chunks.push(buffer);
  }
  const input = decodeInput(JSON.parse(Buffer.concat(chunks).toString('utf8')));
  process.stdout.write(encodeResult(analyze(input), input));
} catch (error) {
  // 仅返回固定原因，不输出源码、异常正文或堆栈。
  process.stdout.write(
    JSON.stringify({
      protocol_version: PROTOCOL_VERSION,
      failure: error instanceof ParseFailure ? error.reason : 'parser_failed',
    }),
  );
  process.exitCode = 2;
}
