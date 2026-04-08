import re

def clean_video_title(title: str) -> str:
    if not title:
        return ""
    
    title = title.split(',')[0]
    title = title.split(' - ')[0]
    title = re.sub(r"\[.*?\]|\(.*?\)", "", title)
    title = re.sub(r"(?i)\b(blu-ray|dvd|4k|uhd|import|widescreen|edition|steelbook|used|new|english|language|vhs)\b", "", title)
    title = title.strip(" -:")
    title = re.sub(r"\s+", " ", title)
    return title.strip()

print(clean_video_title("Dvd Donnie Darko Dvd, Used English Language English"))
print(clean_video_title("The Lord of the Rings: The Fellowship of the Ring - Extended Edition"))
print(clean_video_title("Inception [Blu-ray] (4K UHD)"))
