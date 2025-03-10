
import torch
import torch.nn as nn
class SPConv_3x3(nn.Module):
    def __init__(self, inplanes, outplanes, stride=1, ratio=0.5):
        super(SPConv_3x3, self).__init__()
        self.inplanes_3x3 = int(inplanes*ratio)
        self.inplanes_1x1 = inplanes - self.inplanes_3x3
        self.outplanes_3x3 = int(outplanes*ratio)
        self.outplanes_1x1 = outplanes - self.outplanes_3x3
        self.outplanes = outplanes
        self.stride = stride

        self.gwc = nn.Conv2d(self.inplanes_3x3, self.outplanes, kernel_size=3, stride=self.stride,
                             padding=1, groups=2, bias=False)
        self.pwc = nn.Conv2d(self.inplanes_3x3, self.outplanes, kernel_size=1, bias=False)

        self.conv1x1 = nn.Conv2d(self.inplanes_1x1, self.outplanes,kernel_size=1)
        self.avgpool_s2_1 = nn.AvgPool2d(kernel_size=2,stride=2)
        self.avgpool_s2_3 = nn.AvgPool2d(kernel_size=2, stride=2)
        self.avgpool_add_1 = nn.AdaptiveAvgPool2d(1)
        self.avgpool_add_3 = nn.AdaptiveAvgPool2d(1)
        self.bn1 = nn.BatchNorm2d(self.outplanes)
        self.bn2 = nn.BatchNorm2d(self.outplanes)
        self.ratio = ratio
        self.groups = int(1/self.ratio)
    def forward(self, x):
        b, c, _, _ = x.size()


        x_3x3 = x[:,:int(c*self.ratio),:,:]
        x_1x1 = x[:,int(c*self.ratio):,:,:]
        out_3x3_gwc = self.gwc(x_3x3)
        if self.stride ==2:
            x_3x3 = self.avgpool_s2_3(x_3x3)
        out_3x3_pwc = self.pwc(x_3x3)
        out_3x3 = out_3x3_gwc + out_3x3_pwc
        out_3x3 = self.bn1(out_3x3)
        out_3x3_ratio = self.avgpool_add_3(out_3x3).squeeze(dim=3).squeeze(dim=2)

        # use avgpool first to reduce information lost
        if self.stride == 2:
            x_1x1 = self.avgpool_s2_1(x_1x1)

        out_1x1 = self.conv1x1(x_1x1)
        out_1x1 = self.bn2(out_1x1)
        out_1x1_ratio = self.avgpool_add_1(out_1x1).squeeze(dim=3).squeeze(dim=2)

        out_31_ratio = torch.stack((out_3x3_ratio, out_1x1_ratio), 2)
        out_31_ratio = nn.Softmax(dim=2)(out_31_ratio)
        out = out_1x1 * (out_31_ratio[:,:,1].view(b, self.outplanes, 1, 1).expand_as(out_1x1))\
              + out_3x3 * (out_31_ratio[:,:,0].view(b, self.outplanes, 1, 1).expand_as(out_3x3))

        return out



class SPConv_4x4(nn.Module):
    def __init__(self, inplanes, outplanes, stride=4, ratio=0.5):
        super(SPConv_4x4, self).__init__()
        # 根据比例划分输入通道为用于 4x4 相关卷积和 1x1 卷积的两部分
        self.inplanes_4x4 = int(inplanes * ratio)
        self.inplanes_1x1 = inplanes - self.inplanes_4x4
        # 根据比例划分输出通道为用于 4x4 相关卷积和 1x1 卷积的两部分
        self.outplanes_4x4 = int(outplanes * ratio)
        self.outplanes_1x1 = outplanes - self.outplanes_4x4
        self.outplanes = outplanes
        self.stride = stride

        # 4x4 组卷积，用于处理部分输入通道
        self.gwc = nn.Conv2d(self.inplanes_4x4, self.outplanes, kernel_size=4, stride=self.stride,
                             padding=0, groups=2, bias=False)
        # 4x4 逐点卷积，用于处理部分输入通道
        self.pwc = nn.Conv2d(self.inplanes_4x4, self.outplanes, kernel_size=1, bias=False)

        # 1x1 卷积，用于处理剩余输入通道
        self.conv1x1 = nn.Conv2d(self.inplanes_1x1, self.outplanes, kernel_size=1)
        # 平均池化层，用于下采样
        self.avgpool_s4_1 = nn.AvgPool2d(kernel_size=4, stride=4)
        self.avgpool_s4_4 = nn.AvgPool2d(kernel_size=4, stride=4)
        # 全局平均池化层，用于计算加权比例
        self.avgpool_add_1 = nn.AdaptiveAvgPool2d(1)
        self.avgpool_add_4 = nn.AdaptiveAvgPool2d(1)
        # 批量归一化层，分别对 4x4 卷积和 1x1 卷积的输出进行归一化
        self.bn1 = nn.BatchNorm2d(self.outplanes)
        self.bn2 = nn.BatchNorm2d(self.outplanes)
        self.ratio = ratio
        self.groups = int(1 / self.ratio)

    def forward(self, x):
        # 获取输入特征图的批量大小和通道数
        b, c, _, _ = x.size()

        # 根据比例划分输入特征图为两部分
        x_4x4 = x[:, :int(c * self.ratio), :, :]
        x_1x1 = x[:, int(c * self.ratio):, :, :]

        # 进行 4x4 组卷积
        out_4x4_gwc = self.gwc(x_4x4)
        # 如果步长为 4，对 x_4x4 进行下采样
        if self.stride == 4:
            x_4x4 = self.avgpool_s4_4(x_4x4)
        # 进行 4x4 逐点卷积
        out_4x4_pwc = self.pwc(x_4x4)
        # 将 4x4 组卷积和逐点卷积的结果相加
        out_4x4 = out_4x4_gwc + out_4x4_pwc
        # 对 4x4 卷积结果进行批量归一化
        out_4x4 = self.bn1(out_4x4)
        # 对 4x4 卷积结果进行全局平均池化
        out_4x4_ratio = self.avgpool_add_4(out_4x4).squeeze(dim=3).squeeze(dim=2)

        # 如果步长为 4，对 x_1x1 进行下采样
        if self.stride == 4:
            x_1x1 = self.avgpool_s4_1(x_1x1)

        # 进行 1x1 卷积
        out_1x1 = self.conv1x1(x_1x1)
        # 对 1x1 卷积结果进行批量归一化
        out_1x1 = self.bn2(out_1x1)
        # 对 1x1 卷积结果进行全局平均池化
        out_1x1_ratio = self.avgpool_add_1(out_1x1).squeeze(dim=3).squeeze(dim=2)

        # 将 4x4 卷积和 1x1 卷积的全局平均池化结果堆叠
        out_41_ratio = torch.stack((out_4x4_ratio, out_1x1_ratio), 2)
        # 对堆叠结果进行 Softmax 操作，得到加权比例
        out_41_ratio = nn.Softmax(dim=2)(out_41_ratio)
        # 根据加权比例对 1x1 卷积和 4x4 卷积结果进行加权融合
        out = out_1x1 * (out_41_ratio[:, :, 1].view(b, self.outplanes, 1, 1).expand_as(out_1x1)) \
              + out_4x4 * (out_41_ratio[:, :, 0].view(b, self.outplanes, 1, 1).expand_as(out_4x4))

        return out