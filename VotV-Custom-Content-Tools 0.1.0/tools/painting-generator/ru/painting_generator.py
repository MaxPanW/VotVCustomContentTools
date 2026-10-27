#!/usr/bin/env python3
# VotV Painting Generator — resize images for the four in-game painting slots.
# Requires Python 3.9+ and Pillow.
import os, tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from votv_theme import apply_votv_theme, polish_votv_widgets
from PIL import Image, ImageTk

APP_TITLE = "VotV Painting Generator"
PREVIEW_SIZE = 360
TYPES = {
    "Horizontal — 16:9": ("h", 16, 9),
    "Square — 1:1": ("s", 1, 1),
    "Vertical — 4:5": ("v", 4, 5),
    "Table — 3:4": ("t", 3, 4),
}
RESOLUTIONS = ("Авто (по исходнику)", "512 px по ширине/высоте", "1024 px по ширине/высоте", "2048 px по ширине/высоте")
IMAGE_TYPES = [("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("Все файлы", "*.*")]
def local_assets():
    root = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(root, "VotV", "Assets", "paintings")
def target_size(kind, resolution, original_size):
    folder, rw, rh = TYPES[kind]
    if resolution == RESOLUTIONS[0]:
        # Keep source scale roughly; fit the target aspect ratio using source's larger dimension.
        longside = max(original_size)
        if rw >= rh:
            w = longside
            h = max(1, round(w * rh / rw))
        else:
            h = longside
            w = max(1, round(h * rw / rh))
        return w, h
    side = int(resolution.split()[0])
    if rw >= rh:
        return side, max(1, round(side * rh / rw))
    return max(1, round(side * rw / rh)), side

def has_transparency(im):
    if im.mode in ("RGBA", "LA"):
        return im.getchannel("A").getextrema()[0] < 255
    if im.mode == "P" and "transparency" in im.info:
        return im.convert("RGBA").getchannel("A").getextrema()[0] < 255
    return False

def prepare_image(path, kind, resolution, mode, bg_rgb):
    with Image.open(path) as src:
        src.load()
        original = src.size
        had_alpha = has_transparency(src)
        rgba = src.convert("RGBA")
    size = target_size(kind, resolution, original)
    if mode == "Растянуть":
        resized = rgba.resize(size, Image.Resampling.LANCZOS)
    elif mode == "Вписать (без обрезки)":
        ratio = min(size[0] / rgba.width, size[1] / rgba.height)
        content = rgba.resize((max(1, round(rgba.width*ratio)), max(1, round(rgba.height*ratio))), Image.Resampling.LANCZOS)
        resized = Image.new("RGBA", size, (0,0,0,0))
        resized.alpha_composite(content, ((size[0]-content.width)//2, (size[1]-content.height)//2))
    else: # Заполнить (обрезать края)
        ratio = max(size[0] / rgba.width, size[1] / rgba.height)
        content = rgba.resize((max(1, round(rgba.width*ratio)), max(1, round(rgba.height*ratio))), Image.Resampling.LANCZOS)
        x=(content.width-size[0])//2; y=(content.height-size[1])//2
        resized=content.crop((x,y,x+size[0],y+size[1]))
    # Paintings don't support transparency: composite onto chosen solid background.
    background = Image.new("RGBA", size, (*bg_rgb, 255))
    background.alpha_composite(resized)
    return background.convert("RGB"), {"original": original, "output": size, "had_transparency": had_alpha}

def default_output(kind):
    return os.path.join(local_assets(), TYPES[kind][0])

class PaintingGenerator(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_votv_theme(self)
        self.title(APP_TITLE); self.geometry("1150x880"); self.minsize(980, 800)
        self.files=[]; self.preview_photo=None; self.preview_path=None
        self.bg_rgb=(255,255,255)
        self._ui()
        polish_votv_widgets(self)
        self._preview_placeholder()
    def _ui(self):
        self.columnconfigure(0,weight=1); self.rowconfigure(1,weight=1)
        head=ttk.Frame(self,padding=(16,12,16,6)); head.grid(row=0,column=0,sticky="ew")
        ttk.Label(head,text=APP_TITLE,font=("Segoe UI",16,"bold")).pack(anchor="w")
        ttk.Label(head,text="Подготовка картин для VotV: четыре формата, выбор способа изменения размера и защита от прозрачности.").pack(anchor="w",pady=(4,0))
        body=ttk.Frame(self,padding=16); body.grid(row=1,column=0,sticky="nsew")
        body.columnconfigure(0,weight=3); body.columnconfigure(1,weight=2); body.rowconfigure(0,weight=1)
        left=ttk.Frame(body); left.grid(row=0,column=0,sticky="nsew",padx=(0,14)); left.columnconfigure(0,weight=1)
        fh=ttk.Frame(left); fh.grid(row=0,column=0,sticky="ew",pady=(0,6))
        ttk.Label(fh,text="Изображения",font=("Segoe UI",11,"bold")).pack(side="left")
        ttk.Button(fh,text="＋ Добавить",command=self.add_files).pack(side="right")
        lf=ttk.Frame(left); lf.grid(row=1,column=0,sticky="nsew"); lf.columnconfigure(0,weight=1); lf.rowconfigure(0,weight=1)
        self.lst=tk.Listbox(lf,selectmode=tk.EXTENDED,font=("Segoe UI",10),height=7)
        self.lst.grid(row=0,column=0,sticky="nsew"); self.lst.bind("<<ListboxSelect>>",self.select_file)
        sb=ttk.Scrollbar(lf,orient="vertical",command=self.lst.yview); sb.grid(row=0,column=1,sticky="ns"); self.lst.configure(yscrollcommand=sb.set)
        btn=ttk.Frame(left); btn.grid(row=2,column=0,sticky="ew",pady=(6,10))
        ttk.Button(btn,text="Убрать выбранные",command=self.remove).pack(side="left")
        ttk.Button(btn,text="Очистить список",command=self.clear).pack(side="left",padx=6)
        settings=ttk.LabelFrame(left,text="Формат и обработка",padding=10); settings.grid(row=3,column=0,sticky="ew"); settings.columnconfigure(1,weight=1)
        ttk.Label(settings,text="Тип картины:").grid(row=0,column=0,sticky="w",padx=(0,10),pady=4)
        self.kind=tk.StringVar(value="Horizontal — 16:9")
        self.kindbox=ttk.Combobox(settings,textvariable=self.kind,state="readonly",values=tuple(TYPES.keys()))
        self.kindbox.grid(row=0,column=1,sticky="ew",pady=4); self.kindbox.bind("<<ComboboxSelected>>",self.kind_changed)
        self.ratio_label=ttk.Label(settings,text="Соотношение: 16:9 · папка: paintings/h")
        self.ratio_label.grid(row=1,column=0,columnspan=2,sticky="w",pady=(0,4))
        ttk.Label(settings,text="Разрешение:").grid(row=2,column=0,sticky="w",padx=(0,10),pady=4)
        self.res=tk.StringVar(value=RESOLUTIONS[2])
        self.resbox=ttk.Combobox(settings,textvariable=self.res,state="readonly",values=RESOLUTIONS)
        self.resbox.grid(row=2,column=1,sticky="ew",pady=4); self.resbox.bind("<<ComboboxSelected>>",lambda e:self.refresh())
        ttk.Label(settings,text="Изменение размера:").grid(row=3,column=0,sticky="w",padx=(0,10),pady=4)
        self.mode=tk.StringVar(value="Растянуть")
        self.modebox=ttk.Combobox(settings,textvariable=self.mode,state="readonly",values=("Растянуть","Вписать (без обрезки)","Заполнить (обрезать края)"))
        self.modebox.grid(row=3,column=1,sticky="ew",pady=4); self.modebox.bind("<<ComboboxSelected>>",lambda e:self.refresh())
        ttk.Label(settings,text="Цвет вместо прозрачности:").grid(row=4,column=0,sticky="w",padx=(0,10),pady=4)
        colorrow=ttk.Frame(settings); colorrow.grid(row=4,column=1,sticky="ew")
        self.colorlabel=ttk.Label(colorrow,text="#FFFFFF"); self.colorlabel.pack(side="left")
        ttk.Button(colorrow,text="Выбрать…",command=self.choose_bg).pack(side="right")
        ttk.Label(settings,text="Картины VotV не должны содержать прозрачность. Если у исходника есть прозрачные пиксели, генератор предупредит и заполнит их выбранным цветом (по умолчанию белым).",wraplength=560,foreground="#9a4a00").grid(row=5,column=0,columnspan=2,sticky="w",pady=(7,0))
        out=ttk.LabelFrame(left,text="Папка сохранения",padding=10); out.grid(row=4,column=0,sticky="ew",pady=(10,0)); out.columnconfigure(0,weight=1)
        self.out=tk.StringVar(value=default_output(self.kind.get()))
        ttk.Entry(out,textvariable=self.out).grid(row=0,column=0,sticky="ew")
        ttk.Button(out,text="Обзор…",command=self.choose_out).grid(row=0,column=1,padx=(6,0))
        ttk.Button(out,text="Папка VotV",command=self.set_default).grid(row=0,column=2,padx=(6,0))
        self.runbtn=ttk.Button(left,text="ПОДГОТОВИТЬ КАРТИНЫ",command=self.convert); self.runbtn.grid(row=5,column=0,sticky="ew",pady=(10,0),ipady=7)
        self.status=tk.StringVar(value="Добавь изображения и выбери тип картины.")
        ttk.Label(left,textvariable=self.status,wraplength=600).grid(row=6,column=0,sticky="w",pady=(7,0))
        right=ttk.LabelFrame(body,text="Предпросмотр",padding=12); right.grid(row=0,column=1,sticky="nsew"); right.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(right,width=PREVIEW_SIZE,height=PREVIEW_SIZE,bg="#cccccc",highlightthickness=1,highlightbackground="#888")
        self.canvas.grid(row=0,column=0,sticky="n",pady=(2,10))
        self.info=ttk.Label(right,text="Выбери изображение.",justify="left",wraplength=340); self.info.grid(row=1,column=0,sticky="ew")
        ttk.Label(right,text="Шахматный фон — только предпросмотр. Итоговые картины сохраняются без альфа-канала (RGB).",wraplength=340,foreground="#555").grid(row=2,column=0,sticky="w",pady=(12,0))
    def add_files(self):
        paths=filedialog.askopenfilenames(title="Выбери изображения",filetypes=IMAGE_TYPES)
        added=0
        for p in paths:
            p=os.path.abspath(p)
            if p in self.files: continue
            try:
                with Image.open(p) as im: im.verify()
                self.files.append(p); self.lst.insert(tk.END,os.path.basename(p)); added+=1
            except Exception as e: messagebox.showwarning("Не удалось открыть",f"{os.path.basename(p)}\n\n{e}")
        if added and self.files:
            self.lst.selection_clear(0,tk.END); self.lst.selection_set(0); self.preview_path=self.files[0]
        self.status.set(f"В списке: {len(self.files)} изображений."); self.refresh()
    def select_file(self,_=None):
        sel=self.lst.curselection()
        if sel: self.preview_path=self.files[sel[0]]
        self.refresh()
    def remove(self):
        for i in reversed(self.lst.curselection()):
            self.lst.delete(i); del self.files[i]
        self.preview_path=self.files[0] if self.files else None; self.refresh()
    def clear(self):
        self.files=[]; self.lst.delete(0,tk.END); self.preview_path=None; self.refresh()
    def kind_changed(self,_=None):
        folder,rw,rh=TYPES[self.kind.get()]
        self.ratio_label.configure(text=f"Соотношение: {rw}:{rh} · папка: paintings/{folder}")
        self.out.set(default_output(self.kind.get())); self.refresh()
    def choose_bg(self):
        chosen=colorchooser.askcolor(color="#%02X%02X%02X"%self.bg_rgb,title="Цвет для заполнения прозрачных областей")
        if chosen and chosen[0]:
            self.bg_rgb=tuple(int(v) for v in chosen[0]); self.colorlabel.configure(text=chosen[1] or "Выбран")
            self.refresh()
    def choose_out(self):
        p=filedialog.askdirectory(title="Выбери папку сохранения",initialdir=self.out.get() or os.getcwd())
        if p: self.out.set(p)
    def set_default(self): self.out.set(default_output(self.kind.get()))
    def checker(self):
        s=PREVIEW_SIZE; tile=12
        for y in range(0,s,tile):
            for x in range(0,s,tile):
                c="#eeeeee" if (x//tile+y//tile)%2==0 else "#bbbbbb"
                self.canvas.create_rectangle(x,y,x+tile,y+tile,fill=c,outline=c)
    def _preview_placeholder(self):
        self.canvas.delete("all"); self.checker()
        self.canvas.create_text(PREVIEW_SIZE/2,PREVIEW_SIZE/2,text="Добавь изображение",fill="#444")
    def refresh(self):
        self.canvas.delete("all"); self.checker()
        if not self.preview_path:
            self.canvas.create_text(PREVIEW_SIZE/2,PREVIEW_SIZE/2,text="Добавь изображение",fill="#444"); self.info.configure(text="Выбери изображение."); return
        try:
            img,meta=prepare_image(self.preview_path,self.kind.get(),self.res.get(),self.mode.get(),self.bg_rgb)
            display=img.copy(); display.thumbnail((PREVIEW_SIZE,PREVIEW_SIZE),Image.Resampling.LANCZOS)
            self.preview_photo=ImageTk.PhotoImage(display)
            x=(PREVIEW_SIZE-display.width)//2; y=(PREVIEW_SIZE-display.height)//2
            self.canvas.create_image(x,y,image=self.preview_photo,anchor="nw")
            alpha_note="ВНИМАНИЕ: исходник содержит прозрачность — при сохранении она будет заменена сплошным цветом." if meta["had_transparency"] else "Прозрачность в исходнике не обнаружена."
            self.info.configure(text=f"Исходник: {meta['original'][0]}×{meta['original'][1]}\nРезультат: {meta['output'][0]}×{meta['output'][1]} RGB\nРежим: {self.mode.get()}\n{alpha_note}")
        except Exception as e: self.info.configure(text=f"Ошибка предпросмотра:\n{e}")
    def convert(self):
        if not self.files: messagebox.showinfo("Нет изображений","Сначала добавь хотя бы одно изображение."); return
        dest=self.out.get().strip()
        if not dest: messagebox.showerror("Нет папки","Выбери папку сохранения."); return
        # warn once before processing if any selected source has alpha/transparency
        transparent=[]
        for p in self.files:
            try:
                with Image.open(p) as im:
                    if has_transparency(im): transparent.append(os.path.basename(p))
            except Exception: pass
        if transparent:
            sample="\n".join(transparent[:8])
            more=f"\n…и ещё {len(transparent)-8}" if len(transparent)>8 else ""
            if not messagebox.askyesno("Обнаружена прозрачность",f"Картины VotV не поддерживают прозрачность.\n\nУ {len(transparent)} файлов найдены прозрачные пиксели:\n{sample}{more}\n\nОни будут сведены с выбранным цветом #{self.bg_rgb[0]:02X}{self.bg_rgb[1]:02X}{self.bg_rgb[2]:02X}. Продолжить?"):
                return
        os.makedirs(dest,exist_ok=True); ok=[]; errors=[]
        for p in self.files:
            try:
                result,meta=prepare_image(p,self.kind.get(),self.res.get(),self.mode.get(),self.bg_rgb)
                stem=os.path.splitext(os.path.basename(p))[0]
                out=os.path.join(dest,stem+"_votv.png")
                # avoid overwriting an existing file
                n=2
                while os.path.exists(out):
                    out=os.path.join(dest,f"{stem}_votv_{n}.png"); n+=1
                result.save(out,"PNG",optimize=True)
                ok.append(f"{os.path.basename(out)} ({meta['output'][0]}×{meta['output'][1]})")
            except Exception as e: errors.append(f"{os.path.basename(p)}: {e}")
        self.status.set(f"Готово: {len(ok)} · ошибок: {len(errors)}")
        summary="Успешно обработано: "+str(len(ok))
        if ok: summary+="\n\n"+ "\n".join(ok[:12])
        if len(ok)>12: summary+=f"\n…и ещё {len(ok)-12}"
        if errors: summary+="\n\nОшибки:\n"+"\n".join(errors[:8])
        messagebox.showinfo("Обработка завершена",summary)
if __name__=="__main__":
    PaintingGenerator().mainloop()
