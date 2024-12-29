import re
import os
import json
import asyncio
import aiohttp
from tqdm.asyncio import tqdm

script_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.join(script_dir, "..", "src")
data_dir = os.path.join(script_dir, "..", "data")

GITHUB_API_URL = "https://api.github.com/repos/yackermann/Welikolepie/contents/writers"
REPO_URL = "https://github.com/yackermann/Welikolepie/tree/main/writers"

PANGRAM_RU = "Съешь же ещё этих мягких французских булок, да выпей чаю."

async def get_poems_from_github(session, download_url):
    poems = []
    try:
      async with session.get(download_url) as response:
        response.raise_for_status()
        data = await response.text()
        data = json.loads(data)
        author_id = data["id"]
        for poem in data["poems"].values():
                poem_text = re.sub(r'[\n\r\s]+', ' ', poem["poem"])
                poem_text = re.sub(r'(?:^|\.)\s*\d+\s*\.?(?:\s+|$)', ' ', poem_text)
                poem_text = poem_text.replace(" .", "").replace("_", "").strip()
                poem_text = re.sub(r'\s+', ' ', poem_text)
                # TODO: Не убирать кавычки
                poem_text = poem_text.replace('"', "")

                def lower_wrong_capitals(match):
                    return match.group(0).lower()
                
                poem_text = re.sub(
                    # TODO: Исправить случаи: Тест. "Сеньор" или Тест. (Сеньор)
                    r'(?<!^)(?<![\.\!\?\n])(?<!\.[^\S\n])(?<!\![^\S\n])(?<!\?[^\S\n])[А-ЯA-Z]',
                    lower_wrong_capitals,
                    poem_text
                )

                poems.append(poem_text)

    except KeyError as e:
        print(f"Не удалось найти содержимое поэмы [{e}]: {data.keys()}")
        return None, None
    except aiohttp.ClientError as e:
        print(f"Error fetching data: {e}")
        return None, None
    return author_id, poems


async def create_poetry_json():
    poetry_data = {
        "pangram": [PANGRAM_RU]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GITHUB_API_URL) as response:
                response.raise_for_status()
                files = await response.json()
                tasks = [get_poems_from_github(session, file["download_url"]) for file in files]
                
                results = await tqdm.gather(*tasks, desc="Processing authors")

                for result in results:
                    if result and result[0]:
                        author_id, poems = result
                        poetry_data[author_id] = poems
        
        types = ['lorem: "lorem"']
        for key in poetry_data.keys():
            types.append(f'{key}: "{key}"')
        
        with open(f"{source_dir}/types.typ", "w", encoding="utf-8") as f:
            f.write(f"#let types = ({', '.join(types)})\n")

        with open(f"{data_dir}/data.json", "w", encoding="utf-8") as f:
            json.dump(poetry_data, f, ensure_ascii=False, indent=2)
            
    except aiohttp.ClientError as e:
        print(f"Error fetching author data: {e}")


if __name__ == "__main__":
    asyncio.run(create_poetry_json())
    print("data.json created successfully!")