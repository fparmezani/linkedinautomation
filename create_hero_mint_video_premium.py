import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

class PremiumHeroMintVideoCreator:
    def __init__(self):
        self.base_path = r"C:\Projetos\HeroMint\lib\image-cards"
        self.avatars_data = [
            {"name": "Carlos", "folder": "Carlos", "tagline": "Transforme seu filho\nem um jogador ÉPICO"},
            {"name": "Joao Gabriel", "folder": "Joao Gabriel", "tagline": "Do simples para o\nLEGENDÁRIO em 1 clique"},
            {"name": "Jonas", "folder": "Jonas", "tagline": "Crie cards que\nfazem inveja"},
            {"name": "Miguel", "folder": "Miguel", "tagline": "Viraliza com seu\ncard de futebol"},
        ]
        self.fps = 30
        self.duration_per_transition = 4  # segundos
        self.width = 1080
        self.height = 1920
        self.transition_frames = int(self.fps * self.duration_per_transition * 0.6)  # 60% é transição

    def load_images(self):
        """Carrega as imagens antes e depois"""
        images = {}
        for avatar_info in self.avatars_data:
            avatar_path = Path(self.base_path) / avatar_info["folder"]

            png_files = list(avatar_path.glob("*.png"))
            jpg_files = list(avatar_path.glob("*.jpg"))

            if png_files and jpg_files:
                before_path = jpg_files[0]
                after_path = png_files[0]

                before = cv2.imread(str(before_path))
                after = cv2.imread(str(after_path))

                if before is not None and after is not None:
                    before = self.resize_image(before)
                    after = self.resize_image(after)

                    images[avatar_info["folder"]] = {
                        'before': before,
                        'after': after,
                        'tagline': avatar_info['tagline'],
                        'name': avatar_info['name']
                    }

        return images

    def resize_image(self, img):
        """Redimensiona imagem com fundo gradiente premium"""
        h, w = img.shape[:2]
        aspect = w / h
        target_aspect = self.width / self.height

        if aspect > target_aspect:
            new_w = self.width
            new_h = int(self.width / aspect)
        else:
            new_h = self.height
            new_w = int(self.height * aspect)

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Cria canvas com gradiente premium (azul escuro a roxo)
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for i in range(self.height):
            ratio = i / self.height
            b = int(20 + ratio * 60)
            g = int(20 + ratio * 40)
            r = int(40 + ratio * 80)
            canvas[i, :] = [b, g, r]

        y_offset = (self.height - new_h) // 2
        x_offset = (self.width - new_w) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

        return canvas

    def add_premium_text(self, frame, main_text, sub_text=None, phase="intro"):
        """Adiciona textos premium com efeitos"""
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_frame, 'RGBA')

        try:
            font_main = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 90)
            font_sub = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 50)
            font_brand = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 45)
        except:
            font_main = ImageFont.load_default()
            font_sub = font_main
            font_brand = font_main

        # Texto principal com efeito de sombra 3D
        if phase == "intro" or phase == "middle":
            y_pos = self.height // 3
            text = main_text

            # Sombra colorida
            for offset in range(4, 0, -1):
                alpha = int(100 - offset * 20)
                shadow_color = (100 + offset * 10, 50, 150 - offset * 10, alpha)
                draw.text((self.width//2 + offset, y_pos + offset), text,
                         font=font_main, fill=shadow_color, anchor="mm")

            # Texto principal com gradiente (simulado)
            draw.text((self.width//2, y_pos), text,
                     font=font_main, fill=(255, 255, 100, 255), anchor="mm")

        # Texto comercial
        if phase == "middle" or phase == "outro":
            y_pos = self.height - 400
            text_lines = sub_text.split('\n') if sub_text else []

            for idx, line in enumerate(text_lines):
                line_y = y_pos + (idx * 80)

                # Sombra
                draw.text((self.width//2 + 2, line_y + 2), line,
                         font=font_sub, fill=(0, 0, 0, 200), anchor="mm")

                # Texto com cores vibrantes
                if "ÉPICO" in line or "LEGENDÁRIO" in line or "inveja" in line or "Viraliza" in line:
                    color = (0, 255, 150, 255)  # Verde neon
                else:
                    color = (255, 255, 255, 255)  # Branco

                draw.text((self.width//2, line_y), line,
                         font=font_sub, fill=color, anchor="mm")

        return cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)

    def add_decorative_elements(self, frame, phase=0.5):
        """Adiciona elementos decorativos como bordas e efeitos"""
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_frame, 'RGBA')

        # Linhas decorativas que aparecem durante transição
        line_alpha = int(255 * min(phase, 1))

        # Linha superior
        draw.line([(0, 150), (self.width, 150)],
                 fill=(0, 255, 150, line_alpha), width=3)

        # Linha inferior
        draw.line([(0, self.height - 200), (self.width, self.height - 200)],
                 fill=(255, 100, 200, line_alpha), width=3)

        return cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)

    def add_particle_burst(self, frame, intensity):
        """Adiciona efeito de burst de partículas"""
        frame_copy = frame.copy()

        for _ in range(int(intensity * 30)):
            x = np.random.randint(100, self.width - 100)
            y = np.random.randint(200, self.height - 300)

            # Partículas com cores vibrantes
            colors = [(0, 255, 150), (255, 0, 255), (0, 200, 255), (255, 255, 0)]
            color = random.choice(colors)

            radius = np.random.randint(2, 6)
            cv2.circle(frame_copy, (x, y), radius, color, -1)

        return cv2.addWeighted(frame, 0.85, frame_copy, 0.15, 0)

    def add_glitch_effect(self, frame, intensity):
        """Adiciona efeito de glitch durante transição"""
        if intensity < 0.1 or intensity > 0.9:
            return frame

        h, w = frame.shape[:2]
        glitch_frame = frame.copy()

        # Cria efeito de distorção
        for _ in range(3):
            y_offset = np.random.randint(-5, 5)
            x_offset = np.random.randint(-10, 10)
            height = np.random.randint(20, 60)

            y_start = np.random.randint(0, h - height)
            y_end = y_start + height

            if 0 <= y_start < h and 0 < y_end <= h:
                glitch_frame[y_start:y_end, :] = np.roll(
                    frame[y_start:y_end, :], x_offset, axis=1
                )

        return cv2.addWeighted(frame, 0.9, glitch_frame, 0.1, 0)

    def create_transition_frames(self, before, after, metadata):
        """Cria frames com transição comercial impactante"""
        frames = []

        # FASE 1: Intro com before (1 segundo)
        intro_frames = self.fps
        for i in range(intro_frames):
            frame = before.copy()
            frame = self.add_premium_text(
                frame,
                "VEJA A TRANSFORMAÇÃO",
                phase="intro"
            )
            frame = self.add_decorative_elements(frame, i / intro_frames)
            frame = self.add_glow_effect(frame, 0.3)
            frames.append(frame)

        # FASE 2: Transição dinâmica com efeitos (2.2 segundos)
        transition_duration = int(self.fps * 2.2)
        for i in range(transition_duration):
            progress = i / transition_duration

            # Blend
            frame = cv2.addWeighted(before, 1 - progress, after, progress, 0)

            # Efeitos progressivos
            if progress < 0.3:
                frame = self.add_glitch_effect(frame, progress)
                intensity = progress * 3
            elif progress < 0.7:
                frame = self.add_particle_burst(frame, progress)
                intensity = 1
            else:
                frame = self.add_particle_burst(frame, 1 - progress)
                intensity = 1 - (progress - 0.7) / 0.3

            # Texto dinâmico
            frame = self.add_premium_text(
                frame,
                metadata['tagline'],
                phase="middle"
            )

            frame = self.add_decorative_elements(frame, progress)
            frame = self.add_glow_effect(frame, intensity)
            frames.append(frame)

        # FASE 3: Destaque do after com CTA (0.8 segundos)
        highlight_frames = int(self.fps * 0.8)
        for i in range(highlight_frames):
            frame = after.copy()

            pulse = np.sin((i / highlight_frames) * np.pi) * 0.4
            frame = cv2.addWeighted(frame, 1.0, np.ones_like(frame) * 255, pulse * 0.15, 0)

            frame = self.add_premium_text(
                frame,
                "CLIQUE EM HEROMINT.NET",
                metadata['tagline'],
                phase="outro"
            )
            frame = self.add_particle_burst(frame, 0.7)
            frame = self.add_glow_effect(frame, 0.8)
            frames.append(frame)

        return frames

    def add_glow_effect(self, frame, intensity=0.3):
        """Adiciona efeito de brilho profissional"""
        blurred = cv2.GaussianBlur(frame, (51, 51), 0)
        frame = cv2.addWeighted(frame, 1.0, blurred, intensity, 0)
        return np.clip(frame, 0, 255).astype(np.uint8)

    def add_final_branding(self, frame):
        """Adiciona branding final premium"""
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_frame, 'RGBA')

        try:
            font_brand = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 50)
            font_url = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 40)
        except:
            font_brand = ImageFont.load_default()
            font_url = font_brand

        # Logo/brand
        y_bottom = self.height - 80
        draw.text((self.width // 2, y_bottom), "HEROMINT",
                 font=font_brand, fill=(0, 255, 150, 255), anchor="mm")

        draw.text((self.width // 2, y_bottom + 50), "heromint.net",
                 font=font_url, fill=(255, 255, 255, 200), anchor="mm")

        return cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)

    def create_video(self):
        """Cria o vídeo premium final"""
        print("Carregando imagens...")
        images = self.load_images()

        if not images:
            print("Erro: Nenhuma imagem encontrada!")
            return False

        print(f"Criando video PREMIUM com {len(images)} transformacoes comerciais...")

        output_path = r"C:\Projetos\LinkedinAutomation\HeroMint_BeforeAfter_PREMIUM.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))

        total_frames_created = 0

        for idx, (avatar_key, avatar_data) in enumerate(images.items()):
            print(f"  [{idx + 1}/{len(images)}] Processando {avatar_data['name']}...")

            before = avatar_data['before']
            after = avatar_data['after']

            transition_frames = self.create_transition_frames(before, after, avatar_data)

            for frame in transition_frames:
                frame_final = self.add_final_branding(frame)
                out.write(frame_final)
                total_frames_created += 1

        out.release()

        duration = total_frames_created / self.fps
        print(f"\n[SUCESSO] Video PREMIUM criado com exito!")
        print(f"[INFO] Detalhes:")
        print(f"   - Total de frames: {total_frames_created}")
        print(f"   - Duracao: {duration:.1f} segundos")
        print(f"   - Resolucao: {self.width}x{self.height} (9:16 - Instagram Reels)")
        print(f"   - Localizacao: {output_path}")
        print(f"\n[FEATURES]")
        print(f"   - Textos comerciais impactantes")
        print(f"   - Efeitos de glitch e particulas")
        print(f"   - Transicoes dinamicas")
        print(f"   - Glow e efeitos visuais premium")
        print(f"   - CTA (Call To Action) incluido")

        return True

if __name__ == "__main__":
    creator = PremiumHeroMintVideoCreator()
    creator.create_video()
