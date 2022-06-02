import os
import torch
import argparse

import numpy as np
import torch.nn as nn
import matplotlib.pyplot as plt
import torchvision.datasets as datasets

from loguru import logger
from models.fc import get_fc
from utils import get_device
from tools.plot import plot_mistakes, plot_confusion_matrix
from Task1.utils import make_dir, getFashionMNISTloader, get_idx_to_class


def make_args():
    parser = argparse.ArgumentParser(description="FashionMNIST--FC")
    # --------------------configurations of dataset -------------------------------
    parser.add_argument("--download", action="store_true",
                        help="Enable download dataset")
    parser.add_argument("--valid-split", default=0.2,
                        help="Split ratio of training dataset")
    parser.add_argument("--batch-size", type=int, default=64, metavar="N",
                        help="input batch size for training (default: 64)")
    parser.add_argument("--test-batch-size", type=int, default=128, metavar="N",
                        help="input batch size for testing (default: 1024)")

    # ---------------------configurations of saving------------------------------
    parser.add_argument("--ckpt-file", type=str,
                        help="directory to load checkpoints file")
    parser.add_argument("--ckpts-dir", type=str, default="./ckpts",
                        help="directory to save checkpoints")
    parser.add_argument("--imgs-dir", type=str, default="./imgs",
                        help="directory to save images")
    parser.add_argument("--logs-dir", type=str, default="./logs",
                        help="directory to save log file")
    parser.add_argument("--dataset-root", type=str, default="./data",
                        help="root to datasets")

    # ---------------------configurations of analyzing----------------------------
    parser.add_argument("--plot-mistakes", action="store_true")
    parser.add_argument("--confusion-matrix", action="store_true") 
    return parser


def parse_file(ckpt_file: str):
    """
    Example: Sigmoid_n_1_w_32_None.pth
    """
    file = ckpt_file.split("/")[-1]
    error_msg = "Invalid checkpoint file, file must be in .pth formation"
    assert file.endswith(".pth"), error_msg
    prefix = file[:-4]
    list_params = prefix.split("_")
    act_name, num_hiddens = list_params[0], int(list_params[2])
    width_hiddens, reg_name = int(list_params[4]), "_".join(list_params[5:])
    return prefix, act_name, num_hiddens, width_hiddens, reg_name


def get_mistakes(
    model: nn.Module,
    device,
    dataloader,
):
    model.eval()
    mistakes = []
    with torch.no_grad():
        for imgs, labels in dataloader:
            imgs, labels = imgs.to(device), labels.to(device)
            output = model(imgs)
            preds = output.argmax(dim=1)
            for i, (pred, label) in enumerate(zip(preds, labels)):
                if pred != label.view_as(pred):
                    mistake = {
                        'img': imgs[i],
                        'label': label.item(),
                        'pred': pred.item()
                    }
                    mistakes.append(mistake)
    return mistakes


def get_confusion_matrix(
    model,
    device,
    num_classes,
    dataloader,
):
    model.eval()
    model = model.to(device)
    cm = np.zeros((num_classes, num_classes), dtype=int)
    dataloader = dataloader
    with torch.no_grad():
        for imgs, labels in dataloader:
            imgs, labels = imgs.to(device), labels.to(device)
            outputs = model(imgs)
            _, preds = torch.max(outputs, 1)
            for label, pred in zip(labels.view(-1), preds.view(-1)):
                cm[label.item(), pred.item()] += 1
    return cm


def main():
    args = make_args().parse_args()
    make_dir(args)

    # parse ckpt file and load model
    prefix, act_name, num_hiddens, width_hiddens, reg_name = parse_file(args.ckpt_file)
    in_features, num_classes = 28*28, 10
    width_hiddens = [width_hiddens for _ in range(num_hiddens)]
    device = get_device()
    model = get_fc(
        in_features=in_features,
        width_hiddens=width_hiddens,
        num_classes=num_classes,
        act_name=act_name,
        reg_name=reg_name,
    )
    model.load_state_dict(torch.load(args.ckpt_file))
    _, _, test_loader = getFashionMNISTloader(
        root=args.dataset_root,
        download=args.download,
        batch_size=args.batch_size,
        test_batch_size=args.test_batch_size,
        valid_split=args.valid_split,
    )
    dataset = datasets.FashionMNIST(root=args.dataset_root, train=True)
    idx_to_class = get_idx_to_class(dataset.class_to_idx)

    if args.plot_mistakes:
        # get mistakes
        mistakes = get_mistakes(
            model=model,
            device=device,
            dataloader=test_loader,
        )

        # plot mistakes
        img_file = os.path.join(args.imgs_dir, prefix+"mistakes.svg")
        logger.info(f"Saving image file to {img_file}\n")
        plot_mistakes(
            cmap="gray",
            img_file=img_file,
            mistakes=mistakes,
            num_per_row=8,
            num_instances=64,
            idx_to_class=idx_to_class,
        )
    
    if args.confusion_matrix:
        # get confusion matrix
        cm = get_confusion_matrix(
            model=model,
            device=device,
            num_classes=num_classes,
            dataloader=test_loader,
        )
        # plot confusion matrix
        img_file = os.path.join(args.imgs_dir, "cm.svg")
        plot_confusion_matrix(
            cm=cm,
            xrotation=45,
            cmap=plt.cm.Reds,
            img_file=img_file,
            classes=dataset.classes,
        )


if __name__ == "__main__":
    main()
