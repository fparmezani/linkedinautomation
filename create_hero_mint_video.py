import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os

class HeroMintVideoCreator:
    def __init__(self):
        self.base_path = r"C:\Projetos\HeroMint\lib\image-cards"
        self.avatars = ["Carlos", "Joao Gabriel", "Jonas", "Miguel"]
        self.fps = 30
        self.duration_per_transition = 3  # segundos
        self.total_frames = self.fps * self.duration_per_transition
        self.width = 1080  # Instagram Reels vertical
        self.height = 1920

    def load_images(self):
        """Carrega as imagens antes e depois"""
        images = {}
        for avatar in self.avatars:
            avatar_path = Path(self.base_path) / avatar

            # Encontra as imagens
            png_files = list(avatar_path.glob("*.png"))
            jpg_files = list(avatar_path.glob("*.jpg"))

            if png_files and jpg_files:
                # PNG é o after (card), JPG é o before (original)
                before_path = jpg_files[0]
                after_path = png_files[0]

                before = cv2.imread(str(before_path))
                after = cv2.imread(str(after_path))

                # Resize para o tamanho do video
                before = self.resize_image(before)
                after = self.resize_image(after)

                images[avatar] = {
                    'before': before,
                    'after': after
                }

        return images

    def resize_image(self, img):
        """Redimensiona imagem mantendo aspect ratio e adicionando padding"""
        h, w = img.shape[:2]

        # Calcula o novo tamanho mantendo aspect ratio
        aspect = w / h
        target_aspect = self.width / self.height

        if aspect > target_aspect:
            # Imagem muito larga
            new_w = self.width
            new_h = int(self.width / aspect)
        else:
            # Imagem muito alta
            new_h = self.height
            new_w = int(self.height * aspect)

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Cria canvas com background gradiente
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Preenche com gradiente
        for i in range(self.height):
            color_val = int(20 + (i / self.height) * 30)
            canvas[i, :] = [color_val, color_val, color_val]

        # Coloca a imagem no centro
        y_offset = (self.height - new_h) // 2
        x_offset = (self.width - new_w) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

        return canvas

    def add_text_overlay(self, frame, text, position="top", color=(255, 255, 255)):
        """Adiciona texto ao frame"""
        # Converte para PIL para melhor renderização de texto
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_frame)

        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 60)
        except:
            font = ImageFont.load_default()

        if position == "top":
            text_pos = (self.width // 2, 100)
        elif position == "bottom":
            text_pos = (self.width // 2, self.height - 100)
        else:
            text_pos = position

        # Desenha sombra
        draw.text((text_pos[0]+3, text_pos[1]+3), text, font=font, fill=(0,0,0), anchor="mm")
        # Desenha texto
        draw.text(text_pos, text, font=font, fill=color, anchor="mm")

        return cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)

    def create_transition_frames(self, before, after, avatar_name):
        """Cria frames com transição before/after com efeitos"""
        frames = []

        # Fase 1: Mostra before (0-15 frames)
        phase1_frames = 15
        for i in range(phase1_frames):
            frame = before.copy()
            frame = self.add_text_overlay(frame, "ANTES", position="top", color=(100, 149, 237))
            frame = self.add_glow_effect(frame, intensity=0.3)
            frames.append(frame)

        # Fase 2: Transição com slide e transformação (15-75 frames)
        transition_frames = 60
        for i in range(transition_frames):
            progress = i / transition_frames

            # Efeito de slide combinado com fade
            slide_offset = int(self.width * progress * 0.5)

            # Cria frame com blend
            before_part = before.copy()
            after_part = after.copy()

            # Aplica transformações visuais
            frame = cv2.addWeighted(before_part, 1 - progress, after_part, progress, 0)

            # Adiciona efeito de partículas/brilho na transição
            if progress > 0.3:
                frame = self.add_particle_effect(frame, int(progress * 100))

            # Adiciona texto dinâmico
            text_color = (
                int(100 + (149 * progress)),
                int(149 + (100 * progress)),
                int(237 - (100 * progress))
            )
            if progress < 0.5:
                frame = self.add_text_overlay(frame, "ANTES", position="top", color=(100, 149, 237))
            else:
                frame = self.add_text_overlay(frame, "DEPOIS", position="top", color=(0, 255, 100))

            frame = self.add_glow_effect(frame, intensity=0.5 + progress * 0.5)
            frames.append(frame)

        # Fase 3: Mostra after com destaque (75-90 frames)
        phase3_frames = 15
        for i in range(phase3_frames):
            frame = after.copy()
            frame = self.add_glow_effect(frame, intensity=0.8)
            frame = self.add_text_overlay(frame, "DEPOIS", position="top", color=(0, 255, 100))

            # Adiciona efeito de brilho pulsante
            pulse = np.sin((i / phase3_frames) * np.pi) * 0.3
            frame = cv2.addWeighted(frame, 1.0, np.ones_like(frame) * 255, pulse * 0.1, 0)

            frames.append(frame)

        return frames

    def add_glow_effect(self, frame, intensity=0.3):
        """Adiciona efeito de brilho ao frame"""
        blurred = cv2.GaussianBlur(frame, (51, 51), 0)
        frame = cv2.addWeighted(frame, 1.0, blurred, intensity, 0)
        return np.clip(frame, 0, 255).astype(np.uint8)

    def add_particle_effect(self, frame, count):
        """Adiciona efeito de partículas"""
        frame_copy = frame.copy()

        # Cria partículas aleatórias
        np.random.seed(count)
        for _ in range(min(count // 5, 50)):
            x = np.random.randint(0, self.width)
            y = np.random.randint(0, self.height)
            radius = np.random.randint(2, 8)
            color = (0, 255, 150)
            cv2.circle(frame_copy, (x, y), radius, color, -1)

        # Blend com o frame original
        frame_copy = cv2.addWeighted(frame, 0.8, frame_copy, 0.2, 0)
        return frame_copy

    def add_branding(self, frame):
        """Adiciona branding do HeroMint"""
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_frame)

        try:
            font_small = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 40)
        except:
            font_small = ImageFont.load_default()

        # Adiciona branding no canto inferior
        text = "heromint.net"
        text_pos = (self.width - 100, self.height - 50)

        # Sombra
        draw.text((text_pos[0]+2, text_pos[1]+2), text, font=font_small, fill=(0,0,0), anchor="rm")
        # Texto
        draw.text(text_pos, text, font=font_small, fill=(255, 255, 255), anchor="rm")

        return cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)

    def create_video(self):
        """Cria o vídeo final"""
        print("Carregando imagens...")
        images = self.load_images()

        if not images:
            print("Erro: Nenhuma imagem encontrada!")
            return False

        print(f"Criando vídeo com {len(images)} transformações...")

        # Inicializa o writer de vídeo
        output_path = r"C:\Projetos\LinkedinAutomation\HeroMint_BeforeAfter.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))

        total_frames_created = 0

        for avatar in self.avatars:
            print(f"  Processando {avatar}...")

            before = images[avatar]['before']
            after = images[avatar]['after']

            # Cria frames de transição
            transition_frames = self.create_transition_frames(before, after, avatar)

            # Adiciona branding e escreve frames
            for frame in transition_frames:
                frame_with_branding = self.add_branding(frame)
                out.write(frame_with_branding)
                total_frames_created += 1

        # Libera o writer
        out.release()

        print(f"\n[SUCCESS] Video criado com sucesso!")
        print(f"[INFO] Detalhes:")
        print(f"   - Total de frames: {total_frames_created}")
        print(f"   - Duracao: {total_frames_created / self.fps:.1f} segundos")
        print(f"   - Resolucao: {self.width}x{self.height} (9:16 - Instagram Reels)")
        print(f"   - Localizacao: {output_path}")

        return True

if __name__ == "__main__":
    creator = HeroMintVideoCreator()
    creator.create_video()
