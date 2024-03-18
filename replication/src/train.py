import os, torch, torch.optim as optim

from torch.utils.data import DataLoader
from torch.utils.data.dataset import random_split

from unet_3d import NSN, NDN
from metrics import DiceLoss
from cell_dataset import CellDataset


def run_training_loop(images_dir, ground_truth_dir, criterion, optimizer, num_epochs, model):
    dataset = CellDataset(images_dir=images_dir, masks_dir=ground_truth_dir)

    train_size = int(0.8 * len(dataset))
    eval_size = len(dataset) - train_size
    train_dataset, eval_dataset = random_split(dataset, [train_size, eval_size])

    train_dataloader = DataLoader(train_dataset, batch_size=2, shuffle=True)
    eval_dataloader = DataLoader(eval_dataset, batch_size=2, shuffle=False)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)

    for epoch in range(num_epochs):
        print("epoch: " + str(epoch))

        model.train()
        running_loss = 0.0
        for inputs, labels in train_dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            print(loss)
            optimizer.step()
            running_loss += loss.item()
        epoch_loss = running_loss / len(train_dataloader)
        print(f'Train - Epoch {epoch + 1}/{num_epochs}, Loss: {epoch_loss:.4f}')

        model.eval()
        eval_loss = 0.0
        with torch.no_grad():
            for inputs, labels in eval_dataloader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                eval_loss += loss.item()
        eval_loss /= len(eval_dataloader)
        print(f'Eval - Epoch {epoch + 1}/{num_epochs}, Loss: {eval_loss:.4f}')

    print('Finished Training')


def train_ndn():
    images_dir = os.path.join("data", "images", "train", "Images")
    ground_truth_dir = os.path.join("data", "GroundTruth", "train", "GroundTruth_NDN") # ndn is getting downsampeld too much from kernel size = 5

    n_channels = 1
    model = NDN(n_channels)

    learning_rate = 0.001
    criterion = DiceLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    num_epochs = 10

    run_training_loop(images_dir, ground_truth_dir, criterion, optimizer, num_epochs, model)

def train_nsn():
    images_dir = os.path.join("data", "images", "train", "Images")
    ground_truth_dir = os.path.join("data", "GroundTruth", "train", "GroundTruth_NSN")

    n_channels = 1
    model = NSN(n_channels)

    learning_rate = 0.001
    criterion = DiceLoss()
    optimizer = optim.SGD(model.parameters(), lr=learning_rate)
    num_epochs = 10

    run_training_loop(images_dir, ground_truth_dir, criterion, optimizer, num_epochs, model)


if __name__ == "__main__":
    train_nsn()