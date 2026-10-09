# Flow 中文配音与单一声轨

本流程用于已获得声音文件后的排列和换声。声音由用户选择的 Flow 功能生成；脚本只在本地处理已生成的音频。

## 台词与声音

对每一句记录人物对白或画外旁白、精确中文台词、对应镜头、开始时间和声音文件。对白需与现有口型匹配；旁白可以安排在人物未开口时。用实际声音长度计算结束时间，不用估计台词速度。

本次中文风格示例，可按角色修改：

```text
Speak in natural standard Mandarin Chinese. A warm adult female voice at a comfortable middle pitch. Clear pronunciation, normal conversational delivery and restrained emotion. No singing, whispering, crying or exaggerated emotion.
```

对白“妈，我回来了。”增加 `Slight pause after 妈. Complete the line in about 2 seconds.`。不同句长要改变时长要求。Sulafat 是本次用户选用的 Flow 内置预设，不是原8秒样片声音的克隆。

## 排列与输出

JSON 示例，文件路径相对 JSON 所在目录：

```json
{
  "duration_seconds": 43.25,
  "sample_rate": 48000,
  "voice_source": "Google Flow Sulafat",
  "segments": [
    {"file": "旁白01_多年以后.wav", "start": 0.8, "text": "多年以后，她终于回家。"},
    {"file": "Flow_Sulafat_妈我回来了.wav", "start": 21.25, "text": "妈，我回来了。"}
  ]
}
```

生成 WAV，命令中的 scripts 路径相对技能目录：

```bash
python3 scripts/build_voice_track.py --spec /绝对路径/配音时间线.json --output /绝对路径/完整配音.wav --report /绝对路径/配音验证.json
```

若画面已经完成，可复制画面并置换整条声音：

```bash
python3 scripts/build_voice_track.py --spec /绝对路径/配音时间线.json --output /绝对路径/完整配音.wav --video /绝对路径/已完成画面.mp4 --movie-output /绝对路径/配音成片.mp4
```

脚本不覆盖已有文件，需有明确理由才增加 `--overwrite`。不混入原视频音轨，不改变语速或音高。默认将各段调整至约负18 LUFS目标，短淡入淡出后写入独立样本区间。短台词的实际平均响度可能不同于目标值。

## 验证边界

1. 不把配音叠加到含未知人声的原声中。按互斥区间写入同一条最终 PCM 声轨。
2. 检查每段范围不超过影片，拒绝任何样本重叠。
3. 封装只映射视频 `0:v:0` 与新声音 `1:a:0`。
4. 用 ffprobe 核对音轨数与时长，解码检查文件完整；解码后检查配音区间外是否有残余声音。
5. 对最终播放器试听，确认普通话、语气、声量、杂音及字幕，对嘴型逐帧检查。没有完成这些感官检查时不能称为已核验。

一条 AAC 音轨也可以包含多个人声的混音，因此“只有一条音轨”不是消除叠声的充分证据。
