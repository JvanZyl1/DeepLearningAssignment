import os, torch, torch.optim as optim

from torch.utils.data import DataLoader
from torch.utils.data.dataset import random_split
import matplotlib.pyplot as plt

from unet_3d import NSN, NDN
from metrics import DiceLoss, IoU
from cell_dataset import CellDataset
from tqdm import tqdm


def run_training_loop(images_dir, ground_truth_dir, criterion, optimizer, num_epochs, model):
    dataset = CellDataset(images_dir=images_dir, masks_dir=ground_truth_dir)

    train_size = int(0.8 * len(dataset))
    eval_size = len(dataset) - train_size
    train_dataset, eval_dataset = random_split(dataset, [train_size, eval_size])

    train_dataloader = DataLoader(train_dataset, batch_size=1, shuffle=True)
    eval_dataloader = DataLoader(eval_dataset, batch_size=1, shuffle=False)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)

    train_loss_per_epoch, val_loss_per_epoch, iou_per_5 = [], [], []

    for epoch in range(1, num_epochs + 1):
        print("epoch: " + str(epoch))

        model.train()
        running_loss = 0.0
        for inputs, labels in tqdm(train_dataloader):
            adjust_learning_rate(optimizer, epoch)
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        epoch_loss = running_loss / len(train_dataloader)
        train_loss_per_epoch.append(epoch_loss)
        print(f'Train - Epoch {epoch + 1}/{num_epochs}, Loss: {epoch_loss:.4f}')

        model.eval()
        eval_loss = 0.0
        iou_score = 0
        with torch.no_grad():
            for inputs, labels in tqdm(eval_dataloader):
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                eval_loss += loss.item()
                iou_for_batch = IoU(outputs, labels)
                iou_score += iou_for_batch
        eval_loss /= len(eval_dataloader)
        val_loss_per_epoch.append(eval_loss)
        iou_score /= len(eval_dataloader)
        iou_per_5.append(iou_score)
        print(f'Eval - Epoch {epoch + 1}/{num_epochs}, Loss: {eval_loss:.4f}')

    print('Finished Training')

    return model, train_loss_per_epoch, val_loss_per_epoch, iou_per_5


def adjust_learning_rate(optimizer, epoch, initial_lr=0.1, decay_factor=0.1, decay_epoch=10):
    lr = initial_lr * (decay_factor ** (epoch // decay_epoch))
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr


def train_ndn(images_dir, ground_truth_dir):
    n_channels = 1
    model = NDN(n_channels)

    learning_rate = 0.05
    criterion = DiceLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    num_epochs = 80

    return run_training_loop(images_dir, ground_truth_dir, criterion, optimizer, num_epochs, model)


def train_nsn(images_dir, ground_truth_dir):
    n_channels = 1
    model = NSN(n_channels)

    learning_rate = 0.05
    criterion = DiceLoss()
    optimizer = optim.SGD(model.parameters(), lr=learning_rate)
    num_epochs = 150

    return run_training_loop(images_dir, ground_truth_dir, criterion, optimizer, num_epochs, model)


def plot_train_val_loss(train_loss, val_loss):
    epochs = range(1, len(train_loss) + 1)

    plt.figure(figsize=(10, 6))
    plt.plot(epochs, train_loss, 'bo-', label='Training loss')
    plt.plot(epochs, val_loss, 'r*-', label='Validation loss')
    plt.title('Training and validation loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()

    plt.show()


if __name__ == "__main__":
    images_dir = os.path.join("data", "images", "train", "Images")
    ground_truth_dir = os.path.join("data", "GroundTruth", "train",
                                    "GroundTruth_NDN")  # ndn is getting downsampeld too much from kernel size = 5
    model, train_loss, val_loss, iou_per_epoch = train_ndn(images_dir=images_dir, ground_truth_dir=ground_truth_dir)
    torch.save(model.state_dict(), "ndn.pth")

    print(train_loss)
    print(val_loss)
    print(iou_per_epoch)

    with open("train_loss.txt", 'w') as f:
        for value in train_loss:
            f.write(f"{value}\n")

    with open("val_loss.txt", 'w') as f:
        for value in val_loss:
            f.write(f"{value}\n")

    with open("iou_score.txt", 'w') as f:
        for value in iou_per_epoch:
            f.write(f"{value}\n")