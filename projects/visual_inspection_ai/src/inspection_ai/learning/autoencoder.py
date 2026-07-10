from __future__ import annotations

"""正常画像だけで学習する小型畳み込みAutoencoder。

追加費用なしでRTX GPUを利用できます。これは学習可能なサンプル実装です。
本番採用前に、PatchCore/EfficientAD等との比較と固定テスト評価を行ってください。
"""

from pathlib import Path
from typing import Sequence

import cv2
import numpy as np


def _torch():
    try:
        import torch
        from torch import nn
        from torch.utils.data import Dataset, DataLoader
        return torch, nn, Dataset, DataLoader
    except ImportError as exc:
        raise RuntimeError("GPU版を使用するにはPyTorchを導入してください") from exc


class NormalImageDataset:
    def __new__(cls, paths: Sequence[str | Path], size: int = 128):
        torch, nn, Dataset, DataLoader = _torch()
        class _Dataset(Dataset):
            def __init__(self, paths, size): self.paths=list(paths); self.size=size
            def __len__(self): return len(self.paths)
            def __getitem__(self, idx):
                img=cv2.imread(str(self.paths[idx]),cv2.IMREAD_GRAYSCALE)
                if img is None: raise ValueError(f"画像読込失敗: {self.paths[idx]}")
                img=cv2.resize(img,(self.size,self.size),interpolation=cv2.INTER_AREA).astype(np.float32)/255.0
                return torch.from_numpy(img[None,...])
        return _Dataset(paths,size)


def build_model():
    torch, nn, Dataset, DataLoader = _torch()
    class ConvAE(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder=nn.Sequential(
                nn.Conv2d(1,16,3,2,1),nn.ReLU(),
                nn.Conv2d(16,32,3,2,1),nn.ReLU(),
                nn.Conv2d(32,64,3,2,1),nn.ReLU(),
            )
            self.decoder=nn.Sequential(
                nn.ConvTranspose2d(64,32,4,2,1),nn.ReLU(),
                nn.ConvTranspose2d(32,16,4,2,1),nn.ReLU(),
                nn.ConvTranspose2d(16,1,4,2,1),nn.Sigmoid(),
            )
        def forward(self,x): return self.decoder(self.encoder(x))
    return ConvAE()


def train_autoencoder(paths: Sequence[str | Path], output: str | Path, epochs: int=20, size: int=128, batch_size: int=16):
    torch, nn, Dataset, DataLoader = _torch()
    if len(paths)<5: raise ValueError("Autoencoderには5枚以上の良品画像が必要です")
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ds=NormalImageDataset(paths,size)
    dl=DataLoader(ds,batch_size=min(batch_size,len(ds)),shuffle=True,num_workers=0)
    model=build_model().to(device)
    opt=torch.optim.Adam(model.parameters(),lr=1e-3)
    loss_fn=nn.L1Loss()
    history=[]
    model.train()
    for epoch in range(epochs):
        total=0.0
        for x in dl:
            x=x.to(device); opt.zero_grad(set_to_none=True)
            y=model(x); loss=loss_fn(y,x); loss.backward(); opt.step(); total+=float(loss.item())*len(x)
        history.append(total/len(ds))
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"state_dict":model.state_dict(),"size":size,"history":history,"device":str(device)},out)
    return {"path":str(out),"device":str(device),"final_loss":history[-1],"epochs":epochs}


def anomaly_map(model_path: str | Path, image_bgr: np.ndarray):
    torch, nn, Dataset, DataLoader = _torch()
    ckpt=torch.load(model_path,map_location="cpu",weights_only=False)
    size=int(ckpt["size"]); model=build_model(); model.load_state_dict(ckpt["state_dict"]); model.eval()
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu"); model.to(device)
    gray=cv2.cvtColor(image_bgr,cv2.COLOR_BGR2GRAY)
    x=cv2.resize(gray,(size,size),interpolation=cv2.INTER_AREA).astype(np.float32)/255.0
    tx=torch.from_numpy(x[None,None,...]).to(device)
    with torch.no_grad(): rec=model(tx)
    diff=torch.abs(rec-tx)[0,0].cpu().numpy()
    return diff, float(np.percentile(diff,99))
