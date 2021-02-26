import torch
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms


from tqdm import tqdm

import config.faster_rcnn_res101_config as config
from models.faster_rcnn_resnet101 import create_resnet101_faster_rcnn

#%%
def variable_size_collate(batch):
    data = [item[0] for item in batch]
    b_targets = [item[1]['annotation']['object'] for item in batch]  # each item is a batch item
    target = []
    for item in b_targets:
        t_data = {'labels': [], 'boxes': []}
        for gt in item:
            bb = gt['bndbox']
            t_data['labels'].append(config.CLASSES.index(gt['name']))
            t_data['boxes'].append([int(bb['xmin']), int(bb['ymin']), int(bb['xmax']), int(bb['ymax'])])
        t_data['labels'] = torch.tensor(t_data['labels'], dtype=torch.int64)
        t_data['boxes'] = torch.Tensor(t_data['boxes'])
        target.append(t_data)
    return [data, target]


def run():
    #%% transforms, load dataset and get device
    print('Getting device')
    torch.cuda.empty_cache()
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    #device = torch.device("cpu")

    # %%
    print('Getting model and optimizer')
    model = create_resnet101_faster_rcnn(num_classes=config.NUM_CLASSES)
    #model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
    model.to(device)
    optimizer = optim.SGD(model.parameters(), lr=config.LEARNING_RATE, momentum=config.MOMENTUM)


    transform = transforms.Compose([
        #transforms.Resize(256, 256),
        transforms.ToTensor(),
        transforms.Normalize(config.MEANS, config.STDS),
    ])

    target_transform = transforms.Compose([
        #transforms.ToTensor(),
        #transforms.Resize(256, 256),
    ])

    print('Loading data')
    trainset = torchvision.datasets.VOCDetection(root='./data', image_set='train', year='2007', download=True, transform=transform)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=config.BATCH_SIZE, shuffle=True, num_workers=2, collate_fn=variable_size_collate)
    #%%
    testset = torchvision.datasets.VOCDetection(root='./data', image_set='trainval', year='2007', download=True, transform=transform)
    testloader = torch.utils.data.DataLoader(testset, batch_size=config.BATCH_SIZE, shuffle=False, num_workers=0, collate_fn=variable_size_collate)

    #%%
    print('Starting training...')
    model.train()
    for epoch in range(config.EPOCHS):
        print('Epoch {}'.format(epoch))
        for images, targets in tqdm(trainloader):
            #print('batch')
            #print(images, targets, image_ids)
            images = list(image.to(device) for image in images)
            # it's key:value for t in targets.items
            # This is the format the fasterrcnn expects for targets

            targets = [{'labels': t['labels'].to(device), 'boxes': t['boxes'].to(device)} for t in targets]

            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())
            loss_value = losses.item()

            optimizer.zero_grad()
            losses.backward()
            optimizer.step()

            print("epoch = {}, Training_loss = {}".format(epoch, loss_value))

        print('=' * 10)
        print('=' * 10)
        torch.save(model.state_dict(), config.MODEL_SAVE_PATH)


if __name__ == "__main__":
    run()