"""
Generate 3 synthetic research paper PDFs with controlled content for RAG testing.
Each paper covers ML/AI topics with some overlapping themes for cross-document queries.
"""
import fitz  # PyMuPDF

def create_pdf(filename, title, content_sections):
    """Create a multi-page research paper PDF."""
    doc = fitz.open()
    
    # Page formatting
    page_width, page_height = 595, 842  # A4
    margin = 72
    text_width = page_width - 2 * margin
    
    def add_page_with_text(doc, text):
        page = doc.new_page(width=page_width, height=page_height)
        y = margin
        
        for line in text.split('\n'):
            if y > page_height - margin:
                page = doc.new_page(width=page_width, height=page_height)
                y = margin
            
            # Detect headers vs body text
            fontsize = 11
            fontname = "helv"
            if line.startswith('# '):
                fontsize = 18
                line = line[2:]
                y += 10
            elif line.startswith('## '):
                fontsize = 14
                line = line[3:]
                y += 6
            elif line.startswith('### '):
                fontsize = 12
                line = line[4:]
                y += 4
            
            if line.strip():
                # Word wrap
                words = line.split()
                current_line = ""
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    # Approximate character width
                    if len(test_line) * (fontsize * 0.5) > text_width:
                        page.insert_text((margin, y), current_line, fontsize=fontsize, fontname=fontname)
                        y += fontsize + 4
                        if y > page_height - margin:
                            page = doc.new_page(width=page_width, height=page_height)
                            y = margin
                        current_line = word
                    else:
                        current_line = test_line
                if current_line:
                    page.insert_text((margin, y), current_line, fontsize=fontsize, fontname=fontname)
                    y += fontsize + 4
            else:
                y += 8
    
    full_text = f"# {title}\n\n"
    for section_title, section_body in content_sections:
        full_text += f"## {section_title}\n\n{section_body}\n\n"
    
    add_page_with_text(doc, full_text)
    doc.save(filename)
    doc.close()
    print(f"Created: {filename}")


# ═══════════════════════════════════════════════════════════════
# PAPER 1: Transformer-Based Sentiment Analysis
# ═══════════════════════════════════════════════════════════════
paper1_sections = [
    ("Abstract", 
     "This paper presents SentiFormer, a transformer-based model for multi-class sentiment analysis "
     "on social media text. We achieve state-of-the-art accuracy of 94.7% on the SemEval-2023 benchmark "
     "dataset. Our approach fine-tunes a pre-trained BERT-Large model with a custom attention pooling "
     "mechanism and domain-specific data augmentation. The model was implemented using PyTorch 2.1 "
     "and the Hugging Face Transformers library version 4.35. Training was performed on 4 NVIDIA A100 "
     "GPUs over 48 hours. The key contribution is our novel Contextual Sentiment Attention (CSA) layer "
     "that captures long-range emotional dependencies in text."),

    ("1. Introduction",
     "Sentiment analysis remains a critical task in Natural Language Processing (NLP) with applications "
     "in brand monitoring, political opinion mining, and customer feedback analysis. Traditional approaches "
     "using lexicon-based methods and SVMs achieved limited accuracy of around 78-82%. The advent of "
     "transformer architectures has revolutionized this field. Our work builds upon BERT and introduces "
     "three key innovations: (1) Contextual Sentiment Attention (CSA) layer, (2) domain-adaptive "
     "pre-training on 2.3 million tweets, and (3) a multi-task learning framework that jointly predicts "
     "sentiment polarity and emotional intensity. The main objective of this paper is to demonstrate that "
     "specialized attention mechanisms can significantly improve sentiment classification accuracy beyond "
     "what general-purpose transformers achieve."),

    ("2. Related Work",
     "Prior work in sentiment analysis can be categorized into three eras. The lexicon-based era (2005-2013) "
     "relied on sentiment dictionaries like SentiWordNet. The machine learning era (2013-2018) used SVMs "
     "and Random Forests with TF-IDF features, achieving 82-85% accuracy. The deep learning era (2018-present) "
     "introduced LSTMs and transformers. Kim et al. (2020) used BERT-Base for binary sentiment classification "
     "achieving 91.2% accuracy. Zhang et al. (2022) proposed RoBERTa-Sentiment with 93.1% accuracy. "
     "Our SentiFormer advances beyond these by introducing attention mechanisms specifically designed for "
     "emotional context understanding."),

    ("3. Methodology",
     "Our methodology consists of four main steps. Step 1: Data Collection and Preprocessing - We collected "
     "3.2 million tweets using the Twitter Academic API, filtered to 2.3 million after removing duplicates "
     "and non-English text. Preprocessing included URL removal, emoji conversion to text descriptions, "
     "and hashtag segmentation. Step 2: Domain-Adaptive Pre-training - We further pre-trained BERT-Large "
     "on our tweet corpus using Masked Language Modeling (MLM) with a masking probability of 15% for 3 "
     "epochs. Step 3: Contextual Sentiment Attention (CSA) Layer - We inserted a custom attention layer "
     "between BERT encoder layers 10 and 11. The CSA layer computes attention weights using sentiment-aware "
     "query-key projections: CSA(Q,K,V) = softmax(Q_s * K_s^T / sqrt(d_k)) * V, where Q_s and K_s are "
     "sentiment-projected queries and keys. Step 4: Fine-tuning - The complete model was fine-tuned on "
     "the SemEval-2023 Task 4 dataset with AdamW optimizer, learning rate 2e-5, batch size 32, and "
     "linear warmup over 10% of training steps."),

    ("4. Dataset",
     "We used the SemEval-2023 Task 4 benchmark dataset for evaluation. This dataset contains 58,000 "
     "annotated social media posts across 5 sentiment classes: Very Negative, Negative, Neutral, Positive, "
     "and Very Positive. The dataset was split into 42,000 training samples, 8,000 validation samples, "
     "and 8,000 test samples. Inter-annotator agreement (Cohen's kappa) was 0.87. Additionally, we used "
     "the Stanford Sentiment Treebank (SST-5) dataset containing 11,855 sentences for cross-dataset "
     "evaluation. For domain-adaptive pre-training, we used our custom corpus of 2.3 million unlabeled tweets."),

    ("5. Results",
     "SentiFormer achieved an accuracy of 94.7% on the SemEval-2023 test set, surpassing the previous "
     "state-of-the-art by 1.6 percentage points. On SST-5, we achieved 92.3% accuracy. The F1-score "
     "(macro-averaged) was 0.943 on SemEval and 0.918 on SST-5. Ablation studies showed that removing "
     "the CSA layer reduced accuracy to 93.2% (-1.5%), removing domain-adaptive pre-training reduced "
     "it to 92.8% (-1.9%), and removing both reduced it to 91.5% (-3.2%). The model processes "
     "approximately 1,200 tweets per second during inference on a single A100 GPU. Training cost was "
     "approximately $2,400 in cloud computing resources."),

    ("6. Conclusion",
     "We presented SentiFormer, a transformer-based sentiment analysis model that achieves 94.7% accuracy "
     "through the novel Contextual Sentiment Attention mechanism. Our results demonstrate that domain-specific "
     "attention layers combined with adaptive pre-training significantly improve sentiment classification. "
     "Future work includes extending the approach to multilingual sentiment analysis and exploring "
     "the application of CSA to other NLP tasks such as emotion detection and sarcasm identification.")
]


# ═══════════════════════════════════════════════════════════════
# PAPER 2: Neural Architecture Search for Image Classification
# ═══════════════════════════════════════════════════════════════
paper2_sections = [
    ("Abstract",
     "We introduce EfficientNAS, a neural architecture search framework for image classification that "
     "discovers architectures achieving 97.8% accuracy on CIFAR-100 and 89.2% top-1 accuracy on ImageNet. "
     "Unlike previous NAS methods requiring 3,000+ GPU hours, EfficientNAS completes the search in just "
     "48 GPU hours using a novel progressive search space pruning strategy. The framework was implemented "
     "using TensorFlow 2.12 and trained on 8 NVIDIA V100 GPUs. Our discovered architecture, EfficientNAS-A1, "
     "achieves comparable accuracy to manually designed networks while using 40% fewer parameters. "
     "The key contribution is the Progressive Search Space Pruning (PSSP) algorithm that eliminates "
     "unpromising architecture candidates early in the search process."),

    ("1. Introduction",
     "Neural Architecture Search (NAS) has emerged as a powerful paradigm for automating deep learning "
     "model design. However, the computational cost of NAS remains prohibitive for most researchers. "
     "The original NAS paper by Zoph and Le (2017) required 28,000 GPU hours to discover competitive "
     "architectures. Subsequent works like DARTS (Liu et al., 2019) reduced this to 4 GPU days but "
     "suffered from instability. Our EfficientNAS addresses both challenges. The main objective of "
     "this paper is to develop a computationally efficient NAS method that discovers high-accuracy "
     "architectures in under 50 GPU hours while maintaining search stability. We target image "
     "classification as the primary task, with transfer learning experiments on object detection."),

    ("2. Related Work",
     "NAS research evolved through three main approaches. Reinforcement Learning-based NAS (Zoph and Le, "
     "2017) used an LSTM controller but required 28,000 GPU hours. Evolutionary NAS (Real et al., 2019) "
     "employed genetic algorithms reducing cost to 3,150 GPU hours. Differentiable NAS like DARTS (Liu "
     "et al., 2019) made the search continuous, requiring only 1.5 GPU days but exhibiting performance "
     "collapse. Weight-sharing approaches like ENAS (Pham et al., 2018) achieved 1,000x speedup. Our "
     "PSSP method combines weight-sharing with progressive pruning, offering both speed and stability. "
     "Notably, transformer-based architectures have also been explored for NAS, with ViT-NAS (Chen, 2023) "
     "discovering efficient vision transformer configurations."),

    ("3. Methodology",
     "EfficientNAS operates in three phases. Phase 1: Supernet Training - We construct a supernet "
     "containing all candidate operations (3x3 conv, 5x5 conv, dilated conv, separable conv, skip "
     "connection, max pooling, avg pooling, attention block). The supernet is trained for 100 epochs "
     "using the full CIFAR-100 training set with SGD optimizer, learning rate 0.025, and cosine "
     "annealing schedule. Phase 2: Progressive Search Space Pruning (PSSP) - After every 20 epochs "
     "of supernet training, we evaluate all candidate operations at each layer using a validation "
     "subset. Operations performing below the median are pruned. This reduces the search space by "
     "approximately 50% each round, from 7^14 initially to approximately 2^14 after 4 rounds. "
     "Phase 3: Architecture Selection - From the pruned search space, we perform evolutionary search "
     "with a population size of 50 for 500 generations. Each candidate is evaluated using supernet "
     "weights without retraining. The top architecture is then retrained from scratch for 600 epochs. "
     "The framework uses TensorFlow 2.12 with custom Keras layers for the search space definition."),

    ("4. Dataset",
     "Primary evaluation was performed on CIFAR-100, containing 60,000 32x32 color images across 100 "
     "classes (50,000 training, 10,000 test). We applied standard data augmentation: random cropping, "
     "horizontal flipping, and Cutout regularization. For large-scale evaluation, we used ImageNet "
     "(ILSVRC 2012) containing 1.28 million training images and 50,000 validation images across 1,000 "
     "classes at 224x224 resolution. The ImageNet experiments used RandAugment and MixUp augmentation. "
     "The total dataset size for CIFAR-100 training was approximately 150MB, while the ImageNet "
     "dataset required 150GB of storage."),

    ("5. Results",
     "EfficientNAS-A1 achieved 97.8% accuracy on CIFAR-100 test set and 89.2% top-1 accuracy on "
     "ImageNet validation set. The discovered architecture contains 5.2 million parameters, which is "
     "40% fewer than ResNet-152 (60M params) while achieving 1.3% higher accuracy. Compared to DARTS "
     "(97.2% CIFAR-100), we improve by 0.6% while using 30% less search time. The total search cost "
     "was 48 GPU hours on V100 GPUs, compared to 3,000+ hours for RL-based NAS and 36 GPU hours for "
     "DARTS (but with better stability). The architecture features 14 layers with predominantly 3x3 "
     "separable convolutions and attention blocks in the deeper layers. Inference latency was 2.1ms "
     "per image on V100 and 8.5ms on a consumer RTX 3080 GPU. The training cost for the final "
     "architecture retraining was approximately $1,800 in cloud compute."),

    ("6. Transfer Learning Results",
     "We transferred EfficientNAS-A1 to object detection using Faster R-CNN as the detection head. "
     "On COCO 2017 validation set, the model achieved 42.7 mAP, comparable to ResNeXt-101 backbone "
     "(43.0 mAP) but with 55% fewer FLOPs. Fine-tuning required only 12 epochs compared to 24 epochs "
     "for training from scratch. This demonstrates the strong transferability of NAS-discovered architectures."),

    ("7. Conclusion",
     "EfficientNAS demonstrates that competitive architectures can be discovered in 48 GPU hours through "
     "progressive search space pruning. The discovered EfficientNAS-A1 achieves 97.8% on CIFAR-100 and "
     "89.2% on ImageNet with 40% fewer parameters than comparable manually-designed networks. Future "
     "work will explore multi-objective NAS optimizing for accuracy, latency, and energy consumption "
     "simultaneously.")
]


# ═══════════════════════════════════════════════════════════════
# PAPER 3: Federated Learning for Medical Image Segmentation
# ═══════════════════════════════════════════════════════════════
paper3_sections = [
    ("Abstract",
     "This paper proposes FedMedSeg, a federated learning framework for privacy-preserving medical image "
     "segmentation. We evaluate on brain tumor segmentation using the BraTS 2023 dataset distributed "
     "across 5 simulated hospital nodes. FedMedSeg achieves a Dice score of 0.891, only 1.2% below the "
     "centralized training baseline of 0.903. Our framework uses a modified U-Net architecture with "
     "attention gates and implements Federated Averaging (FedAvg) with differential privacy guarantees "
     "(epsilon = 3.0). The implementation uses PyTorch 2.1 and the Flower federated learning framework "
     "version 1.5. Training was conducted on heterogeneous GPU clusters simulating real hospital "
     "environments. The key contribution is our Adaptive Aggregation Strategy (AAS) that handles "
     "non-IID data distributions across hospital sites."),

    ("1. Introduction",
     "Medical image segmentation is crucial for clinical diagnosis, treatment planning, and surgical "
     "navigation. Deep learning has achieved remarkable results, but training requires large, centralized "
     "datasets — which conflicts with patient privacy regulations like HIPAA and GDPR. Federated learning "
     "offers a solution by enabling model training across distributed hospital sites without sharing raw "
     "patient data. The main objective of this paper is to develop a federated learning framework that "
     "achieves near-centralized accuracy for medical image segmentation while providing formal privacy "
     "guarantees through differential privacy. We focus on brain tumor segmentation as our primary task "
     "due to its clinical importance and the availability of standardized benchmarks. Our approach also "
     "uses transformer-based attention mechanisms within the U-Net architecture to improve segmentation "
     "of small tumor regions."),

    ("2. Related Work",
     "Federated learning was introduced by McMahan et al. (2017) with the FedAvg algorithm. In medical "
     "imaging, Li et al. (2020) applied FedAvg to brain tumor segmentation achieving 0.85 Dice score. "
     "Sheller et al. (2020) demonstrated federated learning across 10 institutions for glioma segmentation. "
     "Privacy-preserving techniques include differential privacy (Abadi et al., 2016) and secure "
     "aggregation (Bonawitz et al., 2017). Recent works combine transformer-based architectures with "
     "federated learning — FedViT (Park et al., 2023) used vision transformers in federated settings "
     "for classification tasks. Our work extends this line of research by incorporating attention-gated "
     "U-Net within a differentially private federated framework, specifically targeting segmentation."),

    ("3. Methodology",
     "FedMedSeg consists of four components. Component 1: Architecture - We use a modified U-Net with "
     "an encoder-decoder structure containing 4 downsampling and 4 upsampling blocks. Attention gates "
     "are inserted at each skip connection to focus on relevant regions. The encoder uses ResNet-34 "
     "blocks pretrained on ImageNet. Total parameters: 31.4 million. Component 2: Federated Training "
     "Protocol - Each hospital trains locally for 5 epochs per communication round using Adam optimizer "
     "with learning rate 1e-4. After local training, model updates (not data) are sent to the central "
     "server. We run 200 communication rounds total. Component 3: Adaptive Aggregation Strategy (AAS) - "
     "Instead of simple averaging, AAS weights each hospital contribution by the inverse of its local "
     "validation loss. Hospitals with better-performing local models contribute more to the global model. "
     "Mathematically: w_global = sum(alpha_i * w_i) where alpha_i = (1/loss_i) / sum(1/loss_j). "
     "Component 4: Differential Privacy - We add calibrated Gaussian noise to model updates before "
     "aggregation. The noise scale is set to achieve (epsilon=3.0, delta=1e-5)-differential privacy "
     "using the moments accountant method. Gradient clipping with max norm of 1.0 is applied before "
     "noise addition."),

    ("4. Dataset",
     "We used the BraTS 2023 (Brain Tumor Segmentation) Challenge dataset. It contains 2,000 multi-modal "
     "MRI scans (T1, T1-Gd, T2, FLAIR) with expert annotations for three tumor sub-regions: enhancing "
     "tumor (ET), tumor core (TC), and whole tumor (WT). Each scan is a 3D volume of 240x240x155 voxels. "
     "We simulated 5 hospital sites by splitting the data using a Dirichlet distribution (alpha=0.5) to "
     "create realistic non-IID partitions. Hospital data sizes ranged from 280 to 520 scans. We used "
     "80/10/10 train/validation/test split at each site. Data augmentation included random flipping, "
     "rotation (up to 15 degrees), and elastic deformation. The total dataset size was approximately "
     "45GB across all modalities."),

    ("5. Results",
     "FedMedSeg achieved Dice scores of 0.891 (whole tumor), 0.847 (tumor core), and 0.812 (enhancing "
     "tumor) on the combined test set. The centralized baseline achieved 0.903, 0.862, and 0.831 "
     "respectively. The gap between federated and centralized training was only 1.2-1.9% across all "
     "sub-regions. Without our AAS, standard FedAvg achieved 0.863 Dice (-2.8% vs centralized), "
     "demonstrating the value of adaptive aggregation. The differential privacy mechanism reduced "
     "accuracy by approximately 0.8% compared to federated training without privacy (0.899 Dice). "
     "Communication overhead was 2.1GB per round for the full model. Using gradient compression "
     "(top-10% sparsification), we reduced this to 210MB per round with only 0.3% accuracy loss. "
     "Training time was 72 hours across the 5-node cluster. The per-hospital training cost was "
     "approximately $500, totaling $2,500 for the entire federation plus $300 for the central server."),

    ("6. Privacy Analysis",
     "We formally analyze the privacy guarantees of FedMedSeg. Using the moments accountant (Abadi et al., "
     "2016), we achieve (epsilon=3.0, delta=1e-5)-differential privacy after 200 communication rounds "
     "with 5 local epochs each. The noise multiplier was set to 0.8 with gradient clipping at norm 1.0. "
     "We also evaluated membership inference attacks: the attacker achieved only 52.3% accuracy (near "
     "random chance of 50%), compared to 68.7% against the centralized model without privacy protection. "
     "This demonstrates strong practical privacy even against sophisticated attacks."),

    ("7. Conclusion",
     "FedMedSeg demonstrates that privacy-preserving federated learning can achieve near-centralized "
     "accuracy for medical image segmentation. The adaptive aggregation strategy effectively handles "
     "non-IID hospital data, and differential privacy provides formal guarantees with minimal accuracy "
     "loss. Future work includes extending to other medical imaging tasks (retinal image analysis, "
     "chest X-ray classification), exploring personalized federated learning where each hospital "
     "maintains a customized model, and reducing communication costs through knowledge distillation.")
]


if __name__ == "__main__":
    create_pdf("Paper1_SentiFormer_Sentiment_Analysis.pdf",
               "SentiFormer: Contextual Sentiment Attention for Multi-Class Social Media Sentiment Analysis",
               paper1_sections)
    
    create_pdf("Paper2_EfficientNAS_Architecture_Search.pdf",
               "EfficientNAS: Progressive Search Space Pruning for Efficient Neural Architecture Search",
               paper2_sections)
    
    create_pdf("Paper3_FedMedSeg_Federated_Learning.pdf",
               "FedMedSeg: Privacy-Preserving Federated Learning for Medical Image Segmentation",
               paper3_sections)
    
    print("\nAll 3 test PDFs created successfully!")
    print("Papers cover overlapping topics: transformers, attention mechanisms, deep learning, datasets")
