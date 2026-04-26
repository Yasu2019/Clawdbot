# LiteLLM Routing Example

Below is an example concept only. The receiving agent must adapt it to the real LiteLLM config style already used.

## Goal
- Keep Ollama for default text models
- Add Lemonade for multimodal or selected API-compatible tasks

## Example routing concept
```yaml
model_list:
  - model_name: qwen-main
    litellm_params:
      model: openai/qwen-main
      api_base: http://127.0.0.1:11434/v1
      api_key: dummy

  - model_name: lemonade-speech
    litellm_params:
      model: openai/lemonade-speech
      api_base: http://127.0.0.1:18070/v1
      api_key: dummy

  - model_name: lemonade-image
    litellm_params:
      model: openai/lemonade-image
      api_base: http://127.0.0.1:18070/v1
      api_key: dummy
```

## Recommended policy
- default text routing -> Ollama
- speech / TTS / image / experimental multimodal -> Lemonade
- no silent cutover
- all new routes must be explicitly named

## Validation points
- does OpenClaw expect chat/completions only?
- are audio and image routes already abstracted?
- does LiteLLM version in use correctly proxy required endpoint types?
